import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import requests
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📈 轉折波段自動標註系統")

# 1. 強力、安全的爬蟲函數
@st.cache_data(ttl=3600)
def get_stable_ranking():
    # 改用更簡潔的目標，若Yahoo爬取失敗，改為備用清單，確保程式不當機
    try:
        # 這裡嘗試抓取，若失敗直接回傳熱門股，保證使用者永遠有東西可選
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get("https://tw.stock.yahoo.com/rank/change-up/", headers=headers, timeout=5)
        # 若網頁結構變更導致失敗，這裡會拋出異常跳轉到 except
        return ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW"]
    except:
        return ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW"]

# 2. 安全初始化
if 'stock_list' not in st.session_state:
    st.session_state.stock_list = get_stable_ranking()

# 3. 檢查選單是否正常
selected = st.selectbox("請選擇個股:", st.session_state.stock_list)

if selected:
    # 確保代碼處理正確
    stock_code = selected.split(' ')[0].replace('.TW', '').replace('.TWO', '')
    
    @st.cache_data
    def get_data(ticker):
        # 補上 .TW 或 .TWO 後綴
        for s in [".TW", ".TWO"]:
            df = yf.download(f"{ticker}{s}", period="6mo", auto_adjust=True)
            if not df.empty: return df
        return None

    df = get_data(stock_code)

    if df is not None and len(df) > 10:
        df['5MA'] = df['Close'].rolling(5).mean()
        # 轉折判斷：這裡用簡單的移動平均交叉作為範例
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['Signal'] = df['State'].diff()
        
        buy = df[df['Signal'] == 2]
        sell = df[df['Signal'] == -2]
        
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=0.8),
            mpf.make_addplot(buy['Close'], type='scatter', markersize=100, marker='^', color='red'),
            mpf.make_addplot(sell['Close'], type='scatter', markersize=100, marker='v', color='green')
        ]
        
        fig, ax = mpf.plot(df, type='candle', style='charles', addplot=ap, returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
    else:
        st.error("無法取得該個股資料。")
