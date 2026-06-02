import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time

# --- 頁面設定 ---
st.set_page_config(layout="wide", page_title="投信鎖碼 V9.2")
st.title("投信鎖碼 V9.2 最終修復版")

# --- 核心邏輯：自動偵測欄位 ---
def get_twse_data():
    today = datetime.today().strftime("%Y%m%d")
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={today}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        return df
    except Exception as e:
        st.error(f"下載失敗: {e}")
        return None

# --- 繪圖函數 ---
def draw_chart(ticker):
    df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
    if df.empty: return
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    fig, ax = mpf.plot(df, type='candle', style='yahoo', returnfig=True, figsize=(10, 5))
    st.pyplot(fig)
    plt.close(fig)

# --- 介面流程 ---
if st.button("🚀 開始選股"):
    with st.spinner("正在讀取證交所資料..."):
        df = get_twse_data()
        if df is not None:
            # 自動找欄位 (不依賴死板名稱)
            cols = df.columns.tolist()
            stock_col = [c for c in cols if '代號' in c][0]
            buy_col = [c for c in cols if '買賣超' in c][0]
            
            df[buy_col] = pd.to_numeric(df[buy_col].str.replace(",", ""), errors="coerce")
            
            # 策略：簡單濾網 (你可以之後再把你的完整邏輯填回來)
            # 這裡我們只篩選出有買超的股票作為範例
            result = df[df[buy_col] > 500].copy()
            st.session_state.results = result[[stock_col, buy_col]]
            st.rerun()

# --- 顯示結果 ---
if 'results' in st.session_state and not st.session_state.results.empty:
    res = st.session_state.results
    # 找代號欄位名稱
    stock_col = res.columns[0]
    
    selected_stock = st.selectbox("選擇股票:", res[stock_col].tolist())
    st.write(f"正在顯示: {selected_stock}")
    draw_chart(selected_stock)
else:
    st.info("請按下按鈕開始選股。")
