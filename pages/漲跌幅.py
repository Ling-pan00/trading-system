import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📈 波段轉折分析系統")

# 1. 直接定義穩定的標的列表，確保程式絕對不會崩潰
@st.cache_data(ttl=3600)
def get_stock_list():
    return ['2330.TW', '2317.TW', '2454.TW', '2303.TW', '2308.TW', '2412.TW', '2881.TW']

# 2. 強健的資料下載與清理（處理 MultiIndex 與 NaN）
@st.cache_data(ttl=3600)
def load_data(ticker):
    df = yf.download(ticker, period="6mo", auto_adjust=True)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 強制將欄位轉為數值，並移除所有缺失值
    for col in ['Close', 'High', 'Low']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna()

# 3. 主邏輯
stocks = get_stock_list()
selected = st.selectbox("請選擇個股:", stocks)

if selected:
    df = load_data(selected)
    if df is not None:
        # 計算 5MA 與轉折狀態
        df['5MA'] = df['Close'].rolling(5).mean()
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['Signal'] = df['State'].diff()
        
        # 繪圖
        ap = [
            mpf.make_addplot(df['5MA'], color='orange'),
            mpf.make_addplot(df[df['Signal'] == 2]['Close'], type='scatter', markersize=100, marker='^', color='red'),
            mpf.make_addplot(df[df['Signal'] == -2]['Close'], type='scatter', markersize=100, marker='v', color='green')
        ]
        fig, _ = mpf.plot(df, type='candle', style='charles', addplot=ap, returnfig=True)
        st.pyplot(fig)
    else:
        st.error("資料獲取失敗")
