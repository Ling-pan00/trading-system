import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import numpy as np # 關鍵：您的繪圖模組需要它

# ==========================================
# 1. 您的「投信鎖碼策略」區 (保持完整)
# ==========================================
def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: pass
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# ==========================================
# 2. 您的「轉折 K 線圖」模組 (原封不動)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    # 這裡放入您那段成功的 draw_zigzag_chart 程式碼
    # (為了節省空間，這裡省略內容，請將您昨天貼給我的整段代碼完整貼在此處)
    pass # <-- 請把您昨天給我的那段 draw_zigzag_chart 函數貼回這裡

# ==========================================
# 3. 整合主程式 (修正 NameError 與狀態)
# ==========================================
st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")

# 用 session_state 儲存結果，解決 NameError
if 'out' not in st.session_state:
    st.session_state.out = pd.DataFrame()

if st.button("開始 V9.2"):
    with st.spinner("策略運算中..."):
        df = load(30)
        # ... (這裡放您原本的篩選邏輯) ...
        # 最後將篩選出來的 result 轉成 DataFrame
        out = pd.DataFrame(result) 
        st.session_state.out = out
        st.rerun()

# 顯示介面
if not st.session_state.out.empty:
    col1, col2 = st.columns([1, 4])
    with col1:
        selected_stock = st.selectbox("選股列表:", st.session_state.out['股票'].tolist())
    with col2:
        # 直接呼叫您這段經過驗證的繪圖函數
        draw_zigzag_chart(f"{selected_stock}.TW", selected_stock)
