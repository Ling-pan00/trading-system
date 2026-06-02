 import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time

# --- 1. 投信鎖碼核心 (完全保留你的原始邏輯) ---
def get_v92_data():
    all_df = []
    # 這裡抓取 30 天資料的邏輯不變
    for i in range(30):
        d = (datetime.today() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.02)
    
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    
    # 欄位解析
    stock_col = [c for c in df.columns if '代號' in c][0]
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        last3, last10 = s[-3:], s[-10:]
        
        # 你的條件判斷 (一個字都沒動)
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    return pd.DataFrame(result).sort_values("強度", ascending=False)

# --- 2. 獨立繪圖函數 (解決 NameError 與 ValueError) ---
def plot_pro_chart(ticker):
    # 嘗試抓取上市或上櫃資料
    symbol = f"{ticker}.TW"
    df = yf.download(symbol, period="3mo", progress=False)
    if df.empty or len(df) < 20: 
        symbol = f"{ticker}.TWO"
        df = yf.download(symbol, period="3mo", progress=False)
    
    if df.empty:
        st.warning(f"找不到 {ticker} 的股價資料，請檢查代號。")
        return

    # 計算均線
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # 繪圖
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df['Close'], label='Close', color='black', alpha=0.3)
    ax.plot(df.index, df['MA5'], label='5MA', color='orange')
    ax.plot(df.index, df['MA10'], label='10MA', color='blue')
    
    # 簡易轉折標記 (H/B)
    highs = (df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))
    lows = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
    ax.scatter(df.index[highs], df['High'][highs], color='red', marker='v', label='H')
    ax.scatter(df.index[lows], df['Low'][lows], color='green', marker='^', label='B')
    
    ax.legend(); ax.grid(True)
    st.pyplot(fig)
    plt.close(fig)

# --- 3. 介面執行 ---
if st.button("執行 V9.2"):
    st.session_state.data = get_v92_data()
    st.rerun()

if 'data' in st.session_state:
    st.dataframe(st.session_state.data)
    sel = st.selectbox("選股:", st.session_state.data["股票"].tolist())
    plot_pro_chart(sel)
