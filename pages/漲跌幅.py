import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

st.set_page_config(layout="wide")
st.title("📈 台股即時排行與轉折分析系統")

# 1. 使用 twstock 獲取漲跌幅排行
@st.cache_data(ttl=600)
def get_rankings():
    # 獲取漲跌幅排行
    top_up = twstock.highest()
    top_down = twstock.lowest()
    
    # 整理為選單格式
    stock_list = []
    for s in top_up: stock_list.append(f"{s['symbol']}.TW (漲幅 {s['change_percent']}%)")
    for s in top_down: stock_list.append(f"{s['symbol']}.TW (跌幅 {s['change_percent']}%)")
    return stock_list

# 2. 資料處理與轉折計算
def get_analysis_data(ticker):
    # 使用 yfinance 下載
    df = yf.download(ticker, period="6mo", auto_adjust=True)
    if df.empty: return None
    
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 計算 5MA 與轉折狀態
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['Signal'] = df['State'].diff()
    return df.dropna()

# 3. UI 介面
stocks = get_rankings()
selected = st.selectbox("請從今日熱門排行選擇個股:", stocks)
code = selected.split(' ')[0]

df = get_analysis_data(code)

if df is not None:
    # 繪圖疊加層：紅箭頭買進、綠箭頭賣出
    ap = [
        mpf.make_addplot(df['5MA'], color='orange', width=0.8),
        mpf.make_addplot(df[df['Signal'] == 2]['Close'], type='scatter', markersize=150, marker='^', color='red'),
        mpf.make_addplot(df[df['Signal'] == -2]['Close'], type='scatter', markersize=150, marker='v', color='green')
    ]
    
    fig, _ = mpf.plot(df, type='candle', style='charles', addplot=ap, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    st.info("💡 紅色 `^` 為價格突破 5MA，綠色 `v` 為跌破 5MA。")
else:
    st.error("無法分析此標的，請稍後再試。")
