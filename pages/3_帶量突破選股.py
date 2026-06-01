import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf

# 設定頁面
st.set_page_config(page_title="全量強勢突破選股", layout="wide")

# 1. 完整 565 檔清單
@st.cache_data
def get_industry_stock_pool():
    return ["1503.TW", "1504.TW", "1513.TW", "1514.TW", "1519.TW", "1521.TW", "1522.TW", "1524.TW", "1525.TW", "1526.TW", "2330.TW", "2454.TW", "3008.TW"] # 為簡化示範已縮減，請自行補回

# --- 最上方控制區 ---
st.title("📊 565 檔強勢帶量突破選股系統")
col1, col2 = st.columns([1, 1])

with col1:
    days = st.slider("選擇歷史天數 (計算週期)", 30, 365, 120)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

# 模擬篩選邏輯 (這裡應串接你的選股判斷邏輯)
stock_pool = get_industry_stock_pool()
# 假設這裡跑過迴圈篩選出符合條件的清單
selected_stocks = stock_pool[:5] 

with col2:
    st.metric("符合條件篩選結果", f"{len(selected_stocks)} 檔")
    st.write(f"資料區間: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

st.divider()

# 核心繪圖函數
def draw_zigzag_chart(df, ticker):
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['10MA'] = df['Close'].rolling(window=10).mean()
    df['20MA'] = df['Close'].rolling(window=20).mean()
    
    # 箭頭提示
    def get_arrow(col):
        return "▲" if df[col].iloc[-1] >= df[col].iloc[-2] else "▼"
    
    st.markdown(f"""
        <div style="background-color: #F0F2F6; padding: 15px; border-radius: 10px; color: black;">
            <div style="display: flex; justify-content: space-around; font-size: 20px; font-weight: bold;">
                <span style="color: #FF8C00;">5MA: {df['5MA'].iloc[-1]:.2f} {get_arrow('5MA')}</span>
                <span style="color: #0000FF;">10MA: {df['10MA'].iloc[-1]:.2f} {get_arrow('10MA')}</span>
            </div>
            <div style="text-align: center; font-size: 20px; font-weight: bold; margin-top: 10px;">
                <span style="color: #800080;">20MA: {df['20MA'].iloc[-1]:.2f} {get_arrow('20MA')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', facecolor='#FFFFFF')
    apds = [mpf.make_addplot(df['5MA'], color='#FF8C00', width=1),
            mpf.make_addplot(df['10MA'], color='#0000FF', width=1),
            mpf.make_addplot(df['20MA'], color='#800080', width=1)]
    
    fig, axlist = mpf.plot(df, type='candle', style=s, addplot=apds, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)

# 主程式執行
selected_ticker = st.selectbox("請選擇要查看的股票", selected_stocks)
if selected_ticker:
    df = yf.download(selected_ticker, start=start_date, end=end_date)
    if not df.empty:
        draw_zigzag_chart(df, selected_ticker)
    else:
        st.error("無法取得該股票資料")
