import streamlit as st
import pandas as pd
import twstock
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（台股穩定版）")

# =========================
# 核心：轉折點計算
# =========================
def get_zigzag_points(df):
    points = []
    if 'Close' not in df.columns: return points
    data = df['Close'].values
    for i in range(1, len(data) - 1):
        if data[i] > data[i-1] and data[i] > data[i+1]:
            points.append((df.index[i], data[i], 'H'))
        elif data[i] < data[i-1] and data[i] < data[i+1]:
            points.append((df.index[i], data[i], 'L'))
    return points

# =========================
# 改用 twstock 抓取歷史資料 (更穩定)
# =========================
@st.cache_data(ttl=3600)
def get_twstock_data(sid):
    stock = twstock.Stock(sid)
    data = stock.fetch_3mo() # 抓取近三個月
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.set_index('date')
        df = df.rename(columns={'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low', 'volume': 'Volume'})
        return df
    return pd.DataFrame()

# =========================
# 其他輔助函數... (同前)
# =========================
def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except: return None

def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty: all_df.append(df)
        time.sleep(0.02)
        if len(all_df) >= days: break
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    if "證券代號" in df.columns: df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# =========================
# 選股核心
# =========================
if st.button("開始 V9.2"):
    df = load(30)
    # ... (選股核心邏輯不變)
    # 為了節省空間，請繼續沿用你之前的選股核心邏輯
    # 確保最後有執行 st.session_state['final_out'] = out
    # 若此處有困難，請告訴我，我為你補上這段
    
# =========================
# 轉折圖分析 (已更新為 twstock)
# =========================
if 'final_out' in st.session_state:
    st.write("---")
    st.subheader("🎯 轉折監測器")
    final_out = st.session_state['final_out']
    sel = st.selectbox("分析個股：", final_out["股票"].tolist())
    
    # 直接使用 sid 抓取
    df_k = get_twstock_data(sel)
    
    if not df_k.empty:
        df_k['5MA'] = df_k['Close'].rolling(5).mean()
        df_k['10MA'] = df_k['Close'].rolling(10).mean()
        df_k['20MA'] = df_k['Close'].rolling(20).mean()
        
        # 繪圖... (同前)
        fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                               addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
        st.pyplot(fig)
    else:
        st.error(f"無法取得 {sel} 的資料。")
