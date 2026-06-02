import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide")
st.title("投信鎖碼 V9.2 最終整合版")

# --- 1. 核心工具：Yahoo 代碼修正 ---
def get_ticker(code):
    return f"{code}.TW" # 預設 TW，若需要判斷上櫃請補強

# --- 2. 您的 V9.2 選股邏輯 ---
def run_v9_2_logic():
    today = datetime.today()
    all_df = []
    # 抓 30 天
    for i in range(40):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.05)
    
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df)
    df["買賣超"] = pd.to_numeric(df["買賣超"].str.replace(",", ""), errors="coerce")
    
    results = []
    for stock, g in df.groupby("證券代號"):
        g = g.sort_values("date")
        s = g["買賣超"].values
        if len(s) < 10: continue
        # 你的鎖碼條件
        if (s[-3:] < 0).sum() >= 2: continue
        if s[-10:].sum() <= 20: continue
        
        results.append({"股票": stock, "強度": s[-3:].sum()})
    return pd.DataFrame(results).sort_values("強度", ascending=False)

# --- 3. 您的繪圖模組 ---
def draw_chart(code, name):
    df = yf.download(f"{code}.TW", period="3mo", progress=False)
    if df.empty: 
        st.error("下載不到資料")
        return
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 畫圖邏輯 (mplfinance)
    mc = mpf.make_marketcolors(up='red', down='green')
    style = mpf.make_mpf_style(marketcolors=mc)
    fig, ax = mpf.plot(df, type='candle', style=style, returnfig=True, figsize=(10,5))
    st.pyplot(fig)
    plt.close(fig)

# --- 4. 穩定介面 ---
if st.button("🚀 開始選股"):
    with st.spinner("掃描中..."):
        st.session_state.result_df = run_v9_2_logic()
        st.rerun()

if 'result_df' in st.session_state and not st.session_state.result_df.empty:
    st.write(f"找到 {len(st.session_state.result_df)} 檔")
    # 下拉選單連結圖表
    sel = st.selectbox("選股:", st.session_state.result_df['股票'].tolist())
    draw_chart(sel, sel)
