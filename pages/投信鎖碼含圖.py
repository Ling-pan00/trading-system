import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np

# --- 1. 您的完整策略碼 (完全沒動) ---
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

# --- 2. 獨立繪圖函式 (修正了後綴問題) ---
def draw_zigzag_chart(ticker_code):
    # 這裡修正了 yfinance 代號識別問題
    code_str = str(ticker_code).strip()
    ticker = f"{code_str}.TW" if int(code_str) < 2000 else f"{code_str}.TWO"
    
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {ticker} 數據，請檢查代號是否正確。")
        return

    # --- 這裡放入您原本的繪圖逻辑 ---
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart = df_chart.dropna().copy()
    fig, axlist = mpf.plot(df_chart, type='candle', volume=True, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    plt.close(fig)

# --- 3. 串接 ---
if st.button("開始 V9.2"):
    df = load(30)
    stock_col, buy_col = find(df, ["證券代號"]), find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    
    out = pd.DataFrame(result)
    st.dataframe(out)

    if not out.empty:
        sel = st.selectbox("選擇股票看圖:", out['股票'].unique())
        if sel:
            draw_zigzag_chart(sel)
