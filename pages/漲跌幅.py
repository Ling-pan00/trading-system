import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="波段轉折分析系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 1. 取得熱門股代號
@st.cache_data(ttl=3600)
def get_popular_stocks():
    return ['2330.TW', '2317.TW', '2454.TW', '2303.TW', '2308.TW', '2382.TW', '2412.TW', '2881.TW']

# 2. 強韌版資料下載函數
@st.cache_data(ttl=3600)
def load_data(ticker):
    end = datetime.today() + timedelta(days=1)
    start = datetime.today() - timedelta(days=180)
    
    # 下載數據
    data = yf.download(ticker, start=start, end=end, auto_adjust=True)
    
    if data is None or data.empty:
        return None
    
    # 處理 MultiIndex 欄位結構
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    # 確保必要欄位存在
    required_cols = ['Close', 'High', 'Low']
    if not all(col in data.columns for col in required_cols):
        return None
        
    # 強制轉換並清除無效行
    for col in required_cols:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    
    return data.dropna()

# 介面
stocks = get_popular_stocks()
selected = st.selectbox("請選擇個股:", stocks)

if selected:
    df = load_data(selected)
    
    if df is not None and len(df) > 10:
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(50).mean() # 調整為50MA增加可視性
        df = df.dropna()
        
        # 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=1.0),
            mpf.make_addplot(df['20MA'], color='purple', width=1.0)
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(10, 6), volume=True)
        st.pyplot(fig)
        
        st.success(f"{selected} 分析完成")
    else:
        st.error("無法取得有效的股價資料，請稍後再試。")
