import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
import requests

# 1. 嚴謹的資料篩選核心 (確保只有真正符合條件的股票)
def get_v92_data():
    all_df = []
    # 抓取最近 30 天數據
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
    
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df)
    
    # 嚴格過濾：移除逗號，確保數值純淨
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    stock_col = [c for c in df.columns if '代號' in c][0]
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    # 你的核心策略：確保邏輯嚴謹
    results = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        last3, last10 = s[-3:], s[-10:]
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        results.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    return pd.DataFrame(results).sort_values("強度", ascending=False)

# 2. 專業繪圖引擎 (加入 H/B 轉折標記與 MA 趨勢)
def plot_professional(ticker):
    try:
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty: df = yf.download(f"{ticker}.TWO", period="3mo", progress=False)
        
        # 計算均線
        for m in [5, 10, 20]: df[f'MA{m}'] = df['Close'].rolling(m).mean()
        
        # 繪圖
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df.index, df['Close'], color='black', alpha=0.3)
        ax.plot(df.index, df['MA5'], color='orange', label='5MA')
        ax.plot(df.index, df['MA10'], color='blue', label='10MA')
        ax.plot(df.index, df['MA20'], color='purple', label='20MA')
        
        # H/B 轉折偵測
        h = (df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))
        b = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
        ax.scatter(df.index[h], df['High'][h], color='red', marker='v', label='H')
        ax.scatter(df.index[b], df['Low'][b], color='green', marker='^', label='B')
        
        ax.legend(); ax.grid(True)
        st.pyplot(fig)
    except Exception as e:
        st.error("該股票目前無有效技術數據，無法繪圖")

# 3. 介面
if st.button("開始 V9.2"):
    st.session_state.data = get_v92_data()
    st.rerun()

if 'data' in st.session_state:
    st.dataframe(st.session_state.data)
    sel = st.selectbox("選擇股票:", st.session_state.data["股票"].tolist())
    plot_professional(sel)
