import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 系統設定
st.set_page_config(page_title="波段轉折分析系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 1. 使用穩定的熱門股清單（避開網頁爬蟲失敗）
@st.cache_data(ttl=3600)
def get_stock_list():
    # 這裡列出您想觀察的熱門個股，確保系統永遠有資料可分析
    return ['2330.TW', '2317.TW', '2454.TW', '2303.TW', '2382.TW', '2308.TW', '2412.TW', '2881.TW']

# 2. 強韌版資料下載函數
@st.cache_data(ttl=3600)
def load_data(ticker):
    end = datetime.today() + timedelta(days=1)
    start = datetime.today() - timedelta(days=180)
    # 下載數據，強制轉換並處理 MultiIndex
    df = yf.download(ticker, start=start, end=end, auto_adjust=True)
    
    if df is None or df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 確保數值型態並移除空值，防止計算崩潰
    for col in ['Close', 'High', 'Low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()

# 3. 介面與邏輯
stocks = get_stock_list()
selected = st.selectbox("請選擇個股:", stocks)

if selected:
    df = load_data(selected)
    
    if df is not None and len(df) > 10:
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna()
        
        # 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=0.8),
            mpf.make_addplot(df['20MA'], color='purple', width=0.8)
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(10, 6), volume=True)
        st.pyplot(fig)
        
        st.success(f"{selected} 分析完成")
    else:
        st.error("無法取得有效的股價資料，請稍後再試。")
