import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np

# ==========================================================
# 1. 您的原始篩選邏輯 (完全不動，直接複製您給我的)
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

def run_strategy():
    df = load(30)
    if df.empty: return pd.DataFrame()
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0 or abs(series[-10:].sum()) < 20: continue
        result.append({"股票": stock})
    return pd.DataFrame(result)

# ==========================================================
# 2. 獨立繪圖函式 (已修復欄位型態轉換)
# ==========================================================
def draw_zigzag_chart(ticker_code):
    try:
        # 強制補後綴
        code_str = str(ticker_code).strip()
        ticker = f"{code_str}.TW" if int(code_str) < 2000 else f"{code_str}.TWO"
        
        df_chart = yf.download(ticker, period="3mo", progress=False)
        
        if df_chart.empty:
            st.error(f"⚠️ 無法取得 {ticker} 數據")
            return

        # --- 關鍵修正：確保所有欄位皆為 float ---
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df_chart.columns:
                df_chart[col] = pd.to_numeric(df_chart[col], errors='coerce')
        
        df_chart = df_chart.dropna()
        
        # 繪圖
        fig, axlist = mpf.plot(df_chart, type='candle', volume=True, returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖錯誤: {e}")

# ==========================================================
# 3. 執行串接
# ==========================================================
st.title("投信鎖碼股 V9.2 (完整整合版)")

if st.button("開始 V9.2"):
    out = run_strategy()
    if not out.empty:
        st.dataframe(out)
        sel = st.selectbox("選擇股票看轉折圖:", out['股票'].unique())
        if sel:
            draw_zigzag_chart(sel)
    else:
        st.warning("目前無符合篩選標的。")
