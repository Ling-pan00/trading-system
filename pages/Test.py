import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

st.title("📈 台股全市場 W 底自動掃描器")

def find_w_bottom(ticker_symbol):
    try:
        # 下載 150 天數據
        df = yf.download(ticker_symbol, period="150d", progress=False)
        if len(df) < 60: return False
        
        # 過濾冷門股
        if df['Volume'].iloc[-1] < 500: return False
        
        close_prices = df['Close'].values.flatten()
        
        # 尋找局部最低點 (order=8 為適中敏感度)
        min_indices = argrelextrema(close_prices, np.less_equal, order=8)[0]
        
        # 確保至少找到兩個低點
        if len(min_indices) >= 2:
            idx1, idx2 = min_indices[-2], min_indices[-1]
            l1, l2 = close_prices[idx1], close_prices[idx2]
            
            # 放寬條件：價差 10% 以內，且兩個低點間隔大於 5 天
            if l1 > 0 and abs(l1 - l2) / l1 < 0.10 and (idx2 - idx1) > 5:
                return True
        return False
    except:
        return False

# 介面操作
if st.button("🚀 開始執行全市場掃描"):
    all_codes = [f"{code}.TW" for code in twstock.codes if len(code) == 4]
    
    # 建議先從前 100 檔開始，確認程式運作正常後，再逐步調大數量
    target_stocks = all_codes[:100] 
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(target_stocks):
        status_text.text(f"正在分析: {ticker} ({i+1}/{len(target_stocks)})")
        
        if find_w_bottom(ticker):
            results.append({"股票代碼": ticker})
        
        # 延遲機制
        time.sleep(0.3)
        progress_bar.progress((i + 1) / len(target_stocks))
    
    status_text.text("掃描完成！")
    
    if results:
        st.success(f"共發現 {len(results)} 檔標的符合 W 底形態：")
        st.table(pd.DataFrame(results))
    else:
        st.warning("本次範圍內未找到符合型態的個股，請嘗試調整參數。")

st.write("---")
st.write("💡 提示：若結果仍然為空，可能是因為市場目前震盪劇烈，W 底型態尚未成形。")
