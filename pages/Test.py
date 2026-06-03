import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

# 設定網頁標題
st.title("📈 台股全市場 W 底自動掃描器")

def find_w_bottom(ticker_symbol):
    try:
        # 下載 120 天日線資料
        df = yf.download(ticker_symbol, period="120d", progress=False)
        if len(df) < 60: return False
        
        # 濾網：只掃描成交量 > 500 張的熱門股
        if df['Volume'].iloc[-1] < 500: return False
        
        close_prices = df['Close'].values.flatten()
        # 尋找局部極小值 (order=10 代表尋找較明顯的波段底部)
        min_indices = argrelextrema(close_prices, np.less_equal, order=10)[0]
        
        if len(min_indices) >= 2:
            l1, l2 = close_prices[min_indices[-2]], close_prices[min_indices[-1]]
            # 判斷：兩個低點價差在 5% 以內 (W底特徵)
            if l1 > 0 and abs(l1 - l2) / l1 < 0.05:
                return True
        return False
    except:
        return False

# 掃描邏輯
if st.button("🚀 開始掃描全市場 (熱門股)"):
    # 自動取得台股所有代碼
    all_codes = [f"{code}.TW" for code in twstock.codes if len(code) == 4]
    
    # 為避免 Timeout，我們暫時先掃描前 100 檔最具代表性的股票
    # 若要全掃，可將 [:100] 去掉，但需注意 Streamlit 執行時間限制
    target_stocks = all_codes
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, ticker in enumerate(target_stocks):
        status_text.text(f"正在分析: {ticker} ({i+1}/{len(target_stocks)})")
        
        if find_w_bottom(ticker):
            results.append({"股票代碼": ticker})
        
        # 每次請求間隔 0.3 秒，避免被 Yahoo 鎖 IP
        time.sleep(0.3)
        progress_bar.progress((i + 1) / len(target_stocks))
    
    # 輸出結果
    status_text.text("掃描完成！")
    if results:
        st.success(f"發現 {len(results)} 檔潛在 W 底個股：")
        st.table(pd.DataFrame(results))
    else:
        st.warning("本次掃描未發現符合條件的熱門股。")
