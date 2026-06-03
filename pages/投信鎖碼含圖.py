import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import requests

# --- 1. 篩選策略 (保留) ---
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
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    return pd.DataFrame(result)

# --- 2. 使用 Plotly 繪圖 (絕對不會崩潰的方案) ---
def draw_chart(stock_id):
    try:
        sid = str(stock_id).strip()
        ticker = f"{sid}.TW" if int(sid) < 2000 else f"{sid}.TWO"
        df = yf.download(ticker, period="3mo", progress=False)
        
        if df.empty:
            st.warning(f"無法抓取 {sid} 資料")
            return

        # 使用 Plotly 繪圖，無需嚴格的 float 轉換
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'])])
        
        fig.update_layout(title=f"{stock_id} 走勢圖", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig)
        
    except Exception as e:
        st.error(f"繪圖錯誤: {e}")

# --- 3. 執行 ---
st.title("投信鎖碼股 V9.2 (最終修正版)")
if st.button("開始 V9.2"):
    out = run_strategy()
    if not out.empty:
        st.dataframe(out)
        sel = st.selectbox("選擇股票看轉折圖:", out['股票'].unique())
        if sel:
            draw_chart(sel)
    else:
        st.warning("目前無符合標的。")
