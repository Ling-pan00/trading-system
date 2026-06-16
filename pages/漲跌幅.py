import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="波段轉折分析系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 1. 取得熱門股代號 (無需爬蟲)
@st.cache_data(ttl=3600)
def get_popular_stocks():
    # 使用熱門權值股清單代替爬蟲
    return ['2330.TW', '2317.TW', '2454.TW', '2303.TW', '2308.TW', '2382.TW', '2412.TW', '2881.TW']

# 2. 下載與清理資料
@st.cache_data
def load_data(ticker):
    end = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    df = yf.download(ticker, start=start, end=end, auto_adjust=True)
    if df.empty: return None
    
    # 確保資料為數值型態
    for col in ['Close', 'High', 'Low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()

# 介面
stocks = get_popular_stocks()
selected = st.selectbox("請選擇個股進行分析:", stocks)

if selected:
    df = load_data(selected)
    
    if df is not None:
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna()
        
        # 波段邏輯：確保均線與收盤價長度一致
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        
        # 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=0.8),
            mpf.make_addplot(df['10MA'], color='black', width=0.8),
            mpf.make_addplot(df['20MA'], color='purple', width=0.8)
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(10, 6), volume=True)
        st.pyplot(fig)
        
        st.write("目前趨勢狀態:", "多頭" if df['State'].iloc[-1] == 1 else "空頭")
    else:
        st.error("無法下載該股票資料，請檢查代號是否正確。")
