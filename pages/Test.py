import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

# 設定頁面標題
st.title("台股 W 底自動偵測器")

def find_w_bottom(ticker_symbol):
    try:
        # 下載近 120 天數據
        df = yf.download(ticker_symbol, period="120d", progress=False)
        if len(df) < 60: return False
        
        # 轉換為 numpy array 以便運算
        close_prices = df['Close'].values.flatten()
        
        # 尋找局部最低點 (order=5 代表左右各 5 天內最低)
        min_indices = argrelextrema(close_prices, np.less_equal, order=5)[0]
        
        if len(min_indices) >= 2:
            idx1, idx2 = min_indices[-2], min_indices[-1]
            l1, l2 = close_prices[idx1], close_prices[idx2]
            
            # 條件：兩個低點價差在 5% 以內，且確保 l1 不為 0
            if l1 > 0 and abs(l1 - l2) / l1 < 0.05:
                return True
        return False
    except Exception as e:
        return False

# 輸入框
stock_code = st.text_input("請輸入股票代碼 (例如 2330.TW):", "2330.TW")

if st.button("開始掃描"):
    with st.spinner('正在分析中...'):
        is_w = find_w_bottom(stock_code)
        if is_w:
            st.success(f"結果：{stock_code} 目前符合 W 底形態特徵！")
            st.balloons()
        else:
            st.warning(f"結果：{stock_code} 目前尚未偵測到明顯的 W 底形態。")

# 顯示技術型態參考
st.write("---")
st.write("### 形態參考示意")
