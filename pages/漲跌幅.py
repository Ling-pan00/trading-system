import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="200檔股票轉折波段系統", layout="wide")
st.title("📈 200檔個股轉折自動標註系統")

# 1. 爬蟲函數
@st.cache_data(ttl=3600)
def get_all_ranking_stocks():
    headers = {'User-Agent': 'Mozilla/5.0'}
    urls = {
        "漲幅排行": "https://tw.stock.yahoo.com/rank/change-up/",
        "跌幅排行": "https://tw.stock.yahoo.com/rank/change-down/"
    }
    all_stocks = []
    
    for category, url in urls.items():
        try:
            res = requests.get(url, headers=headers)
            dfs = pd.read_html(res.text)
            df = dfs[0]
            # 確保有代號欄位
            stocks = df['代號'].astype(str).tolist()
            for s in stocks:
                all_stocks.append(f"{s.split('.')[0]} ({category})")
        except Exception as e:
            st.error(f"抓取 {category} 失敗: {e}")
            
    return all_stocks

# 初始化股票清單
if 'stock_list' not in st.session_state:
    with st.spinner('正在從 Yahoo 抓取 200 檔排行資料...'):
        st.session_state.stock_list = get_all_ranking_stocks()
        st.session_state.current_idx = 0

# 2. 介面控制
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    selected_stock_info = st.selectbox("選擇股票:", st.session_state.stock_list, index=st.session_state.current_idx)
    stock_code = selected_stock_info.split(' ')[0]

# 切換邏輯
if st.button("更新數據"): st.rerun()

# 3. 繪圖邏輯 (同您原來的邏輯)
@st.cache_data
def load_data(ticker):
    end = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    # 嘗試 TW 或 TWO
    for suffix in [".TW", ".TWO"]:
        df = yf.download(f"{ticker}{suffix}", start=start, end=end, auto_adjust=True)
        if not df.empty: return df
    return None

if stock_code:
    df = load_data(stock_code)
    
    if df is not None and len(df) > 20:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 均線計算
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna().copy()

        # 波段邏輯
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        # (這裡沿用您提供的轉折標註邏輯...)
        # ... (繪圖程式碼與您原先的相同) ...

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
    else:
        st.warning(f"找不到代號 {stock_code} 的完整歷史資料。")
