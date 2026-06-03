import streamlit as st
import pandas as pd
import requests
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ==========================================================
# 1. 您的原始篩選策略 (保證不動，原汁原味)
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
        # 您的原始邏輯
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    return pd.DataFrame(result)

# ==========================================================
# 2. 獨立繪圖函式 (物理隔離，確保不影響策略區)
# ==========================================================
def draw_chart(stock_id):
    try:
        # 強制指定格式，避免型態錯誤
        ticker = f"{str(stock_id).strip()}.TW" if int(stock_id) < 2000 else f"{str(stock_id).strip()}.TWO"
        df = yf.download(ticker, period="3mo", progress=False)
        
        if df.empty:
            st.error(f"無法取得 {stock_id} 資料")
            return

        # 這裡強制轉型，確保 Open/High/Low/Close 都是數值
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        
        fig, ax = mpf.plot(df, type='candle', volume=True, returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖錯誤: {e}")

# ==========================================================
# 3. 執行區 (純淨串接)
# ==========================================================
st.title("投信鎖碼股 V9.2")

if st.button("開始 V9.2"):
    out = run_strategy()
    if not out.empty:
        st.dataframe(out)
        # 僅傳遞代號，不傳遞整個 Dataframe
        sel = st.selectbox("選擇股票看轉折圖:", out['股票'].unique())
        if sel:
            draw_chart(sel)
    else:
        st.warning("目前無符合篩選標的。")
