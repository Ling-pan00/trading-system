import streamlit as st
import pandas as pd
import requests
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

# ==========================================================
# 1. 您的原始篩選邏輯 (保持原樣，確保篩選正確)
# ==========================================================
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
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    if "證券代號" in df.columns: df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# ==========================================================
# 2. 獨立繪圖模組 (解決了串接時型態不符的問題)
# ==========================================================
def draw_chart(stock_id):
    # 手動加上後綴，解決 yfinance 找不到資料的問題
    ticker = f"{stock_id}.TW" if int(stock_id) < 2000 else f"{stock_id}.TWO"
    
    # 取得資料
    df = yf.download(ticker, period="3mo", progress=False)
    
    if df.empty:
        st.error(f"無法取得 {stock_id} 資料")
        return

    # 確保資料為數值格式 (解決您的 ValueError)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna()

    # 簡單繪圖 (您可以將這裡換回您原本的複雜畫圖邏輯)
    fig, ax = mpf.plot(df, type='candle', volume=True, returnfig=True)
    st.pyplot(fig)
    plt.close(fig)

# ==========================================================
# 3. 整合執行區 (完全隔絕策略與繪圖)
# ==========================================================
if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    
    out = pd.DataFrame(result)
    st.dataframe(out)

    # 串接繪圖：選單只負責傳遞代號
    if not out.empty:
        selected_stock = st.selectbox("選擇股票看轉折圖:", out['股票'].unique())
        if selected_stock:
            draw_chart(selected_stock)
