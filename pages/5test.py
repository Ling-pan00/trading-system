import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime

# (套件匯入與設定相同，省略重複部分...)

@st.cache_data(ttl=3600) # 盤中即時性調整 ttl 為 1 小時
def get_clean_data(ticker):
    """確保取得最新的交易日數據"""
    df = yf.download(ticker, period="3mo", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=['Close']).sort_index()
    return df

# ... (add_indicators, score, classify_pool, trade_levels 函數請保留您原本的定義)

# ==========================================
# 📊 盤中監控模組 (修正邏輯)
# ==========================================
def run_monitor_optimized(pool_df):
    live_results = []
    for _, row in pool_df.iterrows():
        df = get_clean_data(row["ticker"])
        if len(df) < 6: continue
        
        # 強制使用最後一筆完整收盤資料
        current_data = df.iloc[-1]
        ma5 = df["Close"].rolling(5).mean().iloc[-1]
        
        # 進行邏輯判斷...
        # (在此處使用 current_data['Close'] 確保是正確的最新值)
        # ...
    return pd.DataFrame(live_results)

# ==========================================
# 🎨 轉折 K 線圖繪製模組
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    df_chart = get_clean_data(ticker_code)
    # ... (繪圖邏輯保持不變)
    st.markdown(f"**資料截至：{df_chart.index[-1].strftime('%Y-%m-%d')}**")
    # ... (執行 mpf.plot)

# ==========================================
# 🚀 主程式區 (維持原本選單操作)
# ==========================================
# (在此處依序呼叫上述函數即可)
