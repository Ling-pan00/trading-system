import streamlit as st
import pandas as pd
import requests
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（穩定整合版）")

# ==========================================
# 1. 您的原始核心邏輯 (完全沒動)
# ==========================================
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
    if "證券代號" in df.columns:
        df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# ==========================================
# 2. 您提供的繪圖模組 (獨立掛載)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    # 確保代號正確 (台股加 .TW)
    ticker_full = f"{ticker_code}.TW"
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker_full, start=start_date, end=end_date, progress=False)
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    # 繪圖邏輯 (原封不動)
    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()
    
    # ... (其餘繪圖邏輯照舊，省略以利排版，請放入您原本的完整內容)
    st.pyplot(fig)
    plt.close(fig)

# ==========================================
# 3. 主程式執行 (您的原始邏輯)
# ==========================================
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty: st.error("沒抓到資料"); st.stop()
    
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    # (您的原始篩選迴圈)...
    # (篩選出 result 後)
    
    out = pd.DataFrame(result)
    st.dataframe(out)
    
    # 下拉選單獨立於篩選邏輯之外
    selected_stock = st.selectbox("選擇股票查看轉折圖:", out["股票"].unique())
    if selected_stock:
        draw_zigzag_chart(str(selected_stock), "選定股票")
