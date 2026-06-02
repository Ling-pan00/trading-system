import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np

# --- 頁面配置 ---
st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（整合版）")

# 初始化 session_state
if 'out_df' not in st.session_state:
    st.session_state.out_df = pd.DataFrame()

# =========================
# 您的選股邏輯函數
# =========================
def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except: return None

def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty: all_df.append(df)
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# =========================
# 您的繪圖邏輯函數
# =========================
def draw_zigzag_chart(ticker_code, stock_name):
    df_chart = yf.download(ticker_code, period="3mo", progress=False)
    if df_chart.empty: return
    # (省略部分細節，與您成功的繪圖邏輯相同)
    # ... 此處放入您之前那段能畫出轉折圖的完整繪圖代碼 ...
    st.write(f"正在顯示 {stock_name} 的轉折圖...") 
    # 這裡放 mplfinance 繪圖 code

# =========================
# UI 操作區
# =========================
if st.button("開始 V9.2"):
    with st.spinner("正在運算..."):
        df = load(30)
        stock_col = find(df, ["證券代號"])
        buy_col = find(df, ["買賣超"])
        df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
        
        result = []
        for stock, g in df.groupby(stock_col):
            # ... 放入您的鎖碼邏輯 ...
            # 簡化範例：
            result.append({"股票": stock, "強度": 0.5}) 
            
        st.session_state.out_df = pd.DataFrame(result).sort_values("強度", ascending=False)
        st.rerun()

# =========================
# 結果顯示區
# =========================
if not st.session_state.out_df.empty:
    col1, col2 = st.columns([1, 3])
    with col1:
        selected = st.selectbox("選股列表:", st.session_state.out_df['股票'].tolist())
    with col2:
        draw_zigzag_chart(f"{selected}.TW", selected)
else:
    st.info("請按下按鈕開始選股。")
