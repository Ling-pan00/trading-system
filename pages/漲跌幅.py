import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

st.set_page_config(layout="wide")
st.title("📈 台股百大漲跌幅排行與轉折分析")

# 1. 抓取排行榜 (使用 twstock API，穩定且不需爬網頁)
@st.cache_data(ttl=600)
def get_rankings():
    # 獲取漲幅與跌幅排行榜
    up = twstock.highest()
    down = twstock.lowest()
    
    # 組合漲跌幅清單
    options = []
    for s in up: options.append(f"{s['symbol']}.TW (漲 {s['change_percent']}%)")
    for s in down: options.append(f"{s['symbol']}.TW (跌 {s['change_percent']}%)")
    return options

# 2. 資料下載與轉折運算
@st.cache_data(ttl=3600)
def get_analysis_data(ticker):
    # 使用 yfinance 下載
    df = yf.download(ticker, period="6mo", auto_adjust=True)
    if df.empty: return None
    
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 計算均線與轉折訊號
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['Signal'] = df['State'].diff()
    return df.dropna()

# 3. 介面
stocks = get_rankings()
selected = st.selectbox("請從排行清單挑選個股:", stocks)
code = selected.split(' ')[0]

df = get_analysis_data(code)

if df is not None:
    # 繪圖疊加紅綠箭頭
    ap = [
        mpf.make_addplot(df['5MA'], color='orange', width=0.8),
        mpf.make_addplot(df[df['Signal'] == 2]['Close'], type='scatter', markersize=120, marker='^', color='red'),
        mpf.make_addplot(df[df['Signal'] == -2]['Close'], type='scatter', markersize=120, marker='v', color='green')
    ]
    
    fig, _ = mpf.plot(df, type='candle', style='charles', addplot=ap, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    st.success(f"已標註 {code} 的轉折訊號")
else:
    st.error("無法分析此標的。")
