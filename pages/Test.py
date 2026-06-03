import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

# 定義股票清單 (你可以隨時擴充)
stock_list = ["2330.TW", "2454.TW", "2317.TW", "2303.TW", "2308.TW"]

def find_w_bottom(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="120d", progress=False)
        if len(df) < 60: return False
        close_prices = df['Close'].values.flatten()
        min_indices = argrelextrema(close_prices, np.less_equal, order=5)[0]
        
        if len(min_indices) >= 2:
            l1, l2 = close_prices[min_indices[-2]], close_prices[min_indices[-1]]
            if l1 > 0 and abs(l1 - l2) / l1 < 0.05: # 5% 誤差範圍
                return True
        return False
    except:
        return False

st.title("台股形態自動化掃描器")

if st.button("開始批量掃描"):
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(stock_list):
        is_w = find_w_bottom(ticker)
        if is_w:
            results.append({"股票代碼": ticker, "狀態": "✅ 發現 W 底"})
        
        # 更新進度條
        progress_bar.progress((i + 1) / len(stock_list))
    
    # 呈現結果
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.write("目前清單內無符合 W 底特徵的股票。")
