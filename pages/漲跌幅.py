import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 1. 取得標的 (此處為範例，可替換為實際排行爬蟲結果)
@st.cache_data(ttl=3600)
def get_stocks():
    return ['2330.TW', '2317.TW', '2454.TW', '2303.TW', '2308.TW']

# 2. 資料處理與轉折計算
@st.cache_data
def get_data(ticker):
    df = yf.download(ticker, period="6mo", auto_adjust=True)
    if df.empty: return None
    
    # 確保 MultiIndex 處理
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 計算 5MA 與轉折邏輯 (收盤價大於均線為多頭)
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    
    # 關鍵：計算 Signal (當 State 發生變化時即為轉折點)
    df['Signal'] = df['State'].diff()
    return df.dropna()

selected = st.selectbox("請選擇個股:", get_stocks())
df = get_data(selected)

if df is not None:
    # 篩選出轉折點位
    # 2 代表從 -1 變為 1 (突破均線，紅箭頭)
    # -2 代表從 1 變為 -1 (跌破均線，綠箭頭)
    buy_signals = df[df['Signal'] == 2]
    sell_signals = df[df['Signal'] == -2]
    
    # 設定疊加圖層
    ap = [
        mpf.make_addplot(df['5MA'], color='orange', width=0.8),
        mpf.make_addplot(buy_signals['Close'], type='scatter', markersize=150, marker='^', color='red'),
        mpf.make_addplot(sell_signals['Close'], type='scatter', markersize=150, marker='v', color='green')
    ]
    
    # 繪製圖表
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    
    fig, axlist = mpf.plot(df, type='candle', style=s, add
