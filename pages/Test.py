import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

st.title("🚀 台股全市場 W 底批量篩選器")

def find_w_bottom(ticker_symbol):
    try:
        df = yf.download(ticker_symbol, period="150d", progress=False)
        if len(df) < 60: return False
        if df['Volume'].iloc[-1] < 500: return False
        
        close_prices = df['Close'].values.flatten()
        min_indices = argrelextrema(close_prices, np.less_equal, order=8)[0]
        
        if len(min_indices) >= 2:
            idx1, idx2 = min_indices[-2], min_indices[-1]
            l1, l2 = close_prices[idx1], close_prices[idx2]
            # 寬鬆條件：10% 誤差 + 間隔限制
            if l1 > 0 and abs(l1 - l2) / l1 < 0.10 and (idx2 - idx1) > 5:
                return True
        return False
    except:
        return False

if st.button("開始全市場掃描"):
    all_codes = [f"{code}.TW" for code in twstock.codes if len(code) == 4]
    
    # 將所有股票分成多個 Batch (批次)
    batch_size = 100
    batches = [all_codes[i:i + batch_size] for i in range(0, len(all_codes), batch_size)]
    
    results = []
    progress_bar = st.progress(0)
    total_stocks = len(all_codes)
    
    for b_idx, batch in enumerate(batches):
        st.write(f"正在處理第 {b_idx + 1} 批 ({len(batch)} 檔)...")
        for ticker in batch:
            if find_w_bottom(ticker):
                results.append({"股票代碼": ticker})
            
            # 更新總進度
            progress_bar.progress(len(results) / total_stocks) # 這裡僅作示意
            time.sleep(0.1) # 降低頻率保護 API
            
    if results:
        st.success("掃描完成！發現以下標的：")
        st.table(pd.DataFrame(results))
    else:
        st.warning("全市場掃描完成，未發現符合條件標的。")

st.write("💡 提示：由於全市場股票眾多，這將會花費較長的時間 (可能 5-10 分鐘)。")
