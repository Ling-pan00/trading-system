import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

st.set_page_config(page_title="W底診斷器", layout="wide")
st.title("📊 台股 W 底穩定版選股器")

# 產業映射
industry_map = {
    "半導體": "半導體業", "電子": "電子工業", "電機機械": "電機機械",
    "電器電纜": "電器電纜", "電腦及週邊設備": "電腦及週邊設備業"
}

def get_data_stable(ticker):
    """ 使用 history 方法，對雲端環境更友善 """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="150d")
        if df.empty or len(df) < 60:
            return None
        return df
    except:
        return None

def analyze(ticker):
    df = get_data_stable(ticker)
    if df is None:
        return "無法取得資料", False
    
    close_prices = df['Close'].values.flatten()
    min_indices = argrelextrema(close_prices, np.less_equal, order=5)[0]
    
    if len(min_indices) < 2:
        return "無明顯底部", False
        
    idx1, idx2 = min_indices[-2], min_indices[-1]
    l1, l2 = close_prices[idx1], close_prices[idx2]
    diff = abs(l1 - l2) / l1
    
    if diff < 0.15:
        return f"✅ 符合 (誤差: {diff:.1%})", True
    return f"誤差過大: {diff:.1%}", False

selected_industry = st.selectbox("選擇產業：", list(industry_map.keys()))

if st.button("開始掃描"):
    all_codes = twstock.codes
    target_list = [f"{code}.TW" for code, info in all_codes.items() if info.group == industry_map[selected_industry]]
    
    results = []
    # 進度條控制
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(target_list[:30]): # 先測試 30 檔
        status, is_match = analyze(ticker)
        results.append({"代碼": ticker, "狀態": status})
        progress_bar.progress((i + 1) / 30)
        time.sleep(0.3)
    
    st.table(pd.DataFrame(results))
    st.write("若此處顯示『無法取得資料』，表示該代碼在雲端請求被阻擋。")
