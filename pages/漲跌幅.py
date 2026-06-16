import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="200檔股票轉折波段系統", layout="wide")
st.title("📈 轉折波段自動標註系統")

# 1. 直接使用 yfinance 的篩選功能 (避開爬蟲錯誤)
@st.cache_data(ttl=3600)
def get_market_data():
    # 簡單模擬排行榜，直接由 yfinance 獲取熱門股票代號
    # 這裡以台股權值股與熱門股為例
    symbols = ['2330.TW', '2317.TW', '2454.TW', '6412.TW', '4768.TW', '2303.TW', '2308.TW', '2382.TW']
    return symbols

# 2. 介面選擇
stock_list = get_market_data()
selected = st.selectbox("請選擇個股:", stock_list)

@st.cache_data
def load_data(ticker):
    end = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    df = yf.download(ticker, start=start, end=end, auto_adjust=True)
    return df if not df.empty else None

# 3. 繪圖主邏輯
if selected:
    df = load_data(selected)
    if df is not None:
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna().copy()

        # 波段邏輯
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        
        # 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=0.8),
            mpf.make_addplot(df['10MA'], color='black', width=0.8),
            mpf.make_addplot(df['20MA'], color='purple', width=0.8)
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(12, 7), volume=True)
        st.pyplot(fig)
