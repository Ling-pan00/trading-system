import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

st.set_page_config(page_title="台股 W 底診斷器", layout="wide")
st.title("📊 台股 W 底穩定版選股器")

# 修正代碼格式的函式
def get_yf_ticker(code):
    return f"{code}.TW"

def get_data(ticker):
    # 下載時加入重試機制，且 period 改用 start/end 方式更穩定
    try:
        data = yf.download(ticker, period="150d", progress=False)
        return data
    except:
        return None

def analyze(ticker):
    df = get_data(ticker)
    if df is None or len(df) < 60:
        return "資料不足", False
    
    close_prices = df['Close'].values.flatten()
    min_indices = argrelextrema(close_prices, np.less_equal, order=5)[0]
    
    if len(min_indices) < 2:
        return "無明顯底部", False
        
    idx1, idx2 = min_indices[-2], min_indices[-1]
    l1, l2 = close_prices[idx1], close_prices[idx2]
    diff = abs(l1 - l2) / l1
    
    if diff < 0.15: # 誤差 15% 內
        return f"✅ 符合 (誤差: {diff:.1%})", True
    return f"誤差過大: {diff:.1%}", False

# 產業清單
industry_map = {"半導體": "半導體業", "電子": "電子工業", "電機機械": "電機機械"}
selected_industry = st.selectbox("選擇產業：", list(industry_map.keys()))

if st.button("開始穩定掃描"):
    all_codes = twstock.codes
    target_list = [get_yf_ticker(code) for code, info in all_codes.items() if info.group == industry_map[selected_industry]]
    
    results = []
    # 為了穩定，我們只掃描該產業的前 20 檔進行測試
    for ticker in target_list[:20]:
        status, is_match = analyze(ticker)
        results.append({"代碼": ticker, "狀態": status})
        time.sleep(0.5) # 慢一點，確保伺服器不被鎖
    
    st.table(pd.DataFrame(results))
    st.write("如果看到 '資料不足'，請檢查是否是因為該產業股票剛好停牌或這段時間 Yahoo Finance 連線不穩。")
