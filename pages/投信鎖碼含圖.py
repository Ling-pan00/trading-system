import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 核心數據獲取與清理函式 ---
def fetch_and_clean_data(stock_id):
    # 確保代號正確
    sid = str(stock_id).strip()
    ticker = f"{sid}.TW" if int(sid) < 2000 else f"{sid}.TWO"
    
    # 下載數據
    df = yf.download(ticker, period="3mo", progress=False)
    
    if df is None or df.empty:
        return None
    
    # 強制將所有欄位轉換為數值，並將無法轉換的轉為 NaN
    # 這是解決 "must be ALL float or int" 的關鍵
    cols = ['Open', 'High', 'Low', 'Close']
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # 刪除含有空值的行，確保繪圖資料完整
    df = df.dropna(subset=cols)
    
    return df

# --- 繪圖函式 ---
def draw_chart(df, stock_id):
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])
    fig.update_layout(title=f"{stock_id} 走勢圖", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig)

# --- 主程式 ---
st.title("投信鎖碼股 V9.3")

# [這裡放入您原有的 run_strategy 篩選邏輯]

if st.button("開始"):
    # 假設 out 為 run_strategy 的結果
    out = run_strategy()
    if not out.empty:
        st.dataframe(out)
        sel = st.selectbox("選擇股票:", out['股票'].unique())
        if sel:
            data = fetch_and_clean_data(sel)
            if data is not None and not data.empty:
                draw_chart(data, sel)
            else:
                st.error("未能獲取有效的股票資料，請檢查代號或網路連線。")
