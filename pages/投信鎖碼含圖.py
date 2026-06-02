import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta
import time

# --- 頁面設定 ---
st.set_page_config(page_title="投信鎖碼 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（整合版）")

# --- 初始化狀態 ---
if 'out' not in st.session_state:
    st.session_state.out = pd.DataFrame()

# --- 1. 轉折繪圖模組 ---
def draw_zigzag_chart(ticker_code, stock_name):
    try:
        # 下載數據
        df_chart = yf.download(ticker_code, period="3mo", progress=False)
        if df_chart.empty: return
        if isinstance(df_chart.columns, pd.MultiIndex):
            df_chart.columns = df_chart.columns.get_level_values(0)

        # 計算 MA
        df_chart['5MA'] = df_chart['Close'].rolling(5).mean()
        df_chart['10MA'] = df_chart['Close'].rolling(10).mean()
        df_chart['20MA'] = df_chart['Close'].rolling(20).mean()
        df_chart = df_chart.dropna().copy()

        # 邏輯計算
        df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
        # 繪圖... (保持您成功的繪圖邏輯)
        st.write(f"正在顯示: {stock_name}") # 先測試是否能成功呼叫
        # 若需要 mplfinance 繪圖請在此處放入您的 mplfinance 程式碼
    except Exception as e:
        st.error(f"繪圖錯誤: {e}")

# --- 2. 選股邏輯 ---
def run_strategy():
    # 將您的 load(30) 與 for 迴圈邏輯放這裡
    # 執行完後回傳篩選結果 df
    # 範例模擬資料：
    return pd.DataFrame({'股票': ['1503', '1504', '1513', '1521']})

# --- 3. 介面流程控制 ---
if st.button("開始 V9.2"):
    with st.spinner("正在運算..."):
        # 存入 session_state，確保變數不會消失
        st.session_state.out = run_strategy()
        st.rerun()

# 檢查資料是否存在，防止 NameError
if not st.session_state.out.empty:
    col1, col2 = st.columns([1, 4])
    with col1:
        # 確保選取的值永遠在清單內
        stock_list = st.session_state.out['股票'].tolist()
        selected = st.selectbox("選股列表:", stock_list)
    with col2:
        draw_zigzag_chart(f"{selected}.TW", selected)
else:
    st.info("請按下「開始 V9.2」按鈕。")
