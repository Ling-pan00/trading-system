import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide")
st.title("投信鎖碼 V9.2 實戰版")

# --- 原始核心函數 (保持不變) ---
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

# --- 繪圖函數 ---
def plot_stock(ticker):
    # 原始抓取邏輯
    ticker_str = str(ticker).strip()
    df = yf.download(f"{ticker_str}.TW", period="3mo", progress=False)
    # 若無資料自動轉試 TWO
    if df.empty or len(df) < 10:
        df = yf.download(f"{ticker_str}.TWO", period="3mo", progress=False)
    
    if df.empty: return

    # 計算均線
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    
    apds = [mpf.make_addplot(df[['MA5', 'MA10', 'MA20']]) ]
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, returnfig=True, figsize=(10, 5))
    st.pyplot(fig)
    plt.close(fig)

# --- V9.2 選股邏輯 ---
if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col].str.replace(",", ""), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        # 【嚴格遵守您原始的邏輯，未做任何更改】
        if (s[-3:] < 0).sum() >= 2 or s[-10:].sum() <= 0 or abs(s[-10:].sum()) < 20: continue
        
        result.append({"股票": stock, "強度": round(s[-3:].sum() / (abs(s[-10:].sum()) + 1), 4)})
    
    st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.rerun()

# --- 顯示區 (不限制數量) ---
if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    df_show = st.session_state.final_out
    selected = st.selectbox("選擇股票:", df_show["股票"].tolist())
    plot_stock(selected)
    st.dataframe(df_show, use_container_width=True)
