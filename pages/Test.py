import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

# 核心判斷邏輯
def find_w_bottom(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="120d", progress=False)
        if len(df) < 60: return False
        
        # 濾網：成交量過濾
        if df['Volume'].iloc[-1] < 500: return False
        
        close_prices = df['Close'].values.flatten()
        # 找極小值
        min_indices = argrelextrema(close_prices, np.less_equal, order=10)[0]
        
        if len(min_indices) >= 2:
            l1, l2 = close_prices[min_indices[-2]], close_prices[min_indices[-1]]
            # 寬鬆條件：誤差放寬到 8%
            if l1 > 0 and abs(l1 - l2) / l1 < 0.08:
                return True
        return False
    except:
        return False

st.title("🚀 台股全市場 W 底批量篩選器")

if st.button("開始掃描"):
    # 獲取全台股代碼
    all_codes = [f"{code}.TW" for code in twstock.codes if len(code) == 4]
    
    results = []
    # 這裡我們為了避免超時，先跑前 200 檔，你可以視需求調整
    target_stocks = all_codes[:200] 
    
    bar = st.progress(0)
    for i, ticker in enumerate(target_stocks):
        if find_w_bottom(ticker):
            results.append({"股票代碼": ticker})
        
        bar.progress((i + 1) / len(target_stocks))
        # 避免被 Yahoo 封鎖
        if i % 10 == 0: time.sleep(1) 
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.write("本次範圍內未找到符合型態的個股，請嘗試調整參數。")
