import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt

st.set_page_config(page_title="投信鎖碼股整合版", layout="wide")
st.title("投信鎖碼股 V9.2 (含轉折分析)")

# =========================
# 1. 您的篩選邏輯 (完全不動)
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
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    if "證券代號" in df.columns: df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# =========================
# 2. 您的繪圖模組 (完全不動)
# =========================
def draw_zigzag_chart(ticker_code):
    # 這裡自動判定 TW/TWO
    ticker = f"{ticker_code}.TW" if int(ticker_code) < 2000 else f"{ticker_code}.TWO"
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker, start=start_date, end=end_date, progress=False)
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {ticker_code} 數據")
        return

    # 計算均線與轉折 (您的邏輯)
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna().copy()
    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()

    # 繪圖
    fig, axlist = mpf.plot(df_chart, type='candle', volume=True, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    plt.close(fig)

# =========================
# 3. 整合執行
# =========================
if st.button("開始 V9.2"):
    df = load(30)
    stock_col, buy_col = find(df, ["證券代號"]), find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0 or abs(series[-10:].sum()) < 20: continue
        
        result.append({"股票": stock, "近3日買超": int(series[-3:].sum())})
    
    out = pd.DataFrame(result)
    st.dataframe(out)

    # 串接繪圖功能
    if not out.empty:
        sel = st.selectbox("選擇股票看轉折圖:", out['股票'].unique())
        if sel:
            draw_zigzag_chart(sel)
