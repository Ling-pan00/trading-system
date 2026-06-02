import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta
import time

# --- 設定頁面 ---
st.set_page_config(layout="wide")
st.title("DEBUG 診斷模式：V9.2")

# --- 1. 狀態持久化 ---
if 'out_df' not in st.session_state:
    st.session_state.out_df = pd.DataFrame()

# --- 2. 測試用的選股邏輯 ---
def run_selection():
    st.write(">> 正在執行 run_selection...")
    # 這是模擬資料，如果這段跑得動，問題出在您原本的 load() 函數裡
    time.sleep(1)
    return pd.DataFrame({'股票': ['1503', '1504', '1513', '1521']})

# --- 3. 測試按鈕 ---
if st.button("開始 V9.2 (測試版)"):
    st.write(">> 按鈕已被按下！")
    try:
        # 強制執行選股
        df = run_selection()
        st.session_state.out_df = df
        st.write(">> 資料已寫入 session_state")
        st.rerun() # 強制重跑
    except Exception as e:
        st.error(f"執行時崩潰: {e}")
else:
    st.write("按鈕等待中...")

# --- 4. 顯示結果 ---
if not st.session_state.out_df.empty:
    st.success("成功取得資料！")
    st.dataframe(st.session_state.out_df)
else:
    st.warning("目前無資料，請點擊按鈕。")
