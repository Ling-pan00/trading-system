import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V9.2 專業版", layout="wide")
st.title("投信鎖碼 V9.2（技術轉折實戰版）")

# --- 初始化 ---
if 'final_out' not in st.session_state:
    st.session_state.final_out = pd.DataFrame()

# --- 原始核心函數 ---
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
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# --- 繪圖邏輯：MA 線 + H/B 轉折標記 ---
def plot_technical_chart(ticker):
    ticker_str = str(ticker).strip()
    df = pd.DataFrame()
    for suffix in ['.TW', '.TWO']:
        df = yf.download(f"{ticker_str}{suffix}", period="3mo", progress=False)
        if not df.empty and len(df) > 20: break
    
    if df.empty:
        st.warning("查無 K 線資料")
        return

    # 計算 MA
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # 繪製圖表
    apds = [
        mpf.make_addplot(df['MA5'], color='orange', width=1),
        mpf.make_addplot(df['MA10'], color='blue', width=1),
        mpf.make_addplot(df['MA20'], color='purple', width=1)
    ]
    
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, 
                       volume=True, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    plt.close(fig)

# --- V9.2 原始選股邏輯 (無限制檔數) ---
if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col].str.replace(",", ""), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        try:
            g = g.sort_values("date")
            series = g[buy_col].values
            if len(series) < 10: continue
            
            last3, last10 = series[-3:], series[-10:]
            if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
            
            result.append({
                "股票": stock,
                "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4),
                "穩定度": round(last10.sum() / (abs(last3.sum()) + 1), 4)
            })
        except: continue
    
    st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.rerun()

# --- 顯示結果 ---
if not st.session_state.final_out.empty:
    df_show = st.session_state.final_out
    selected = st.selectbox("選擇股票:", df_show["股票"].tolist())
    plot_technical_chart(selected)
    st.dataframe(df_show, use_container_width=True)
