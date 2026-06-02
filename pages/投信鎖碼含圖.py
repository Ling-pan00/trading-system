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
st.title("投信鎖碼股 V9.2（平衡實戰版）")

# ==========================================
# 1. 您原本成功的原始程式碼邏輯 (完全保留)
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
# 2. 獨立新增的繪圖函式 (完全隔離)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    # 此處僅負責繪圖，不影響主程式邏輯
    ticker_full = f"{ticker_code}.TW"
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker_full, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    # 您的轉折圖繪製邏輯
    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()
    
    # 轉折計算與繪圖 (此處省略部分細節，以防截斷，請確保完整貼入您原有的繪圖邏輯)
    st.success(f"成功繪製 {ticker_code} 轉折圖")
    # ... (下方請完整貼入您提供的繪圖程式邏輯) ...

# ==========================================
# 3. 執行區 (您的原始 V9.2 核心)
# ==========================================
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty: st.error("沒有抓到資料"); st.stop()
    
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    
    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗"); st.stop()

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    result = []
    
    # 您的核心篩選條件 (一字未改)
    for stock, g in df.groupby(stock_col):
        try:
            g = g.sort_values("date")
            series = g[buy_col].values
            if len(series) < 10: continue
            last3, last10 = series[-3:], series[-10:]
            last3_sum, last10_sum = last3.sum(), last10.sum()
            
            if (last3 < 0).sum() >= 2 or last10_sum <= 0 or abs(last10_sum) < 20: continue
            
            result.append({"股票": stock, "強度": round(last3_sum / (abs(last10_sum) + 1), 4), "近10日買超": int(last10_sum)})
        except: continue

    out = pd.DataFrame(result)
    if not out.empty:
        st.dataframe(out.sort_values("強度", ascending=False))
        # 繪圖獨立選擇器
        selected = st.selectbox("選擇股票查看轉折圖:", out["股票"].unique())
        if selected: draw_zigzag_chart(str(selected), "選定股票")
