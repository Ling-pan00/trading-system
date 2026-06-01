import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf

# 確保股票池完整
def get_industry_stock_pool():
    # 這裡填入你完整確認的 530 檔代碼
    return ["1503.TW", "1504.TW", "2303.TW", "2317.TW", "..."] 

# 核心掃描與穩健處理
def run_scan():
    pool = get_industry_stock_pool()
    results = []
    # 設定下載參數，增加 thread 處理加速
    df_raw = yf.download(pool, period="3mo", group_by='ticker', threads=True)
    
    for s_id in pool:
        try:
            df = df_raw[s_id]
            if df.empty or len(df) < 22: continue
            
            # 你的原始策略邏輯
            # 務必加上針對資料完整性的檢查
            ...
        except Exception:
            continue # 若單檔失敗，直接跳過，不影響整體運作
    return results

# 繪圖保護機制
def plot_stock(s_id):
    df = yf.download(s_id, period="3mo")
    if df.empty:
        st.error("無法取得該檔股票資料")
        return
    # 繪圖前檢查資料格式
    ...
