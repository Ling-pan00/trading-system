import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
from datetime import datetime, timedelta

st.set_page_config(page_title="三池強力監控系統", layout="wide")
st.title("🚀 三池強力監控系統")

# --- 1. 選股與資料準備 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

if "results" not in st.session_state: st.session_state["results"] = pd.DataFrame()

if st.button("🚀 執行強力選股"):
    results = []
    tickers = [s["ticker"] for s in get_stock_list()]
    ticker_map = {s["ticker"]: s for s in get_stock_list()}
    with st.spinner("正在掃描..."):
        for t in tickers[:100]:
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                c, ma5 = float(df["Close"].iloc[-1]), df["Close"].rolling(5).mean().iloc[-1]
                if c > ma5: results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t})
            except: continue
    st.session_state["results"] = pd.DataFrame(results)

# --- 2. 顯示系統 ---
if not st.session_state["results"].empty:
    # 盤中監控區
    st.write("---")
    st.subheader("📈 盤中動能監控")
    if st.button("🔄 更新監控"):
        live_data = []
        for _, row in st.session_state["results"].head(10).iterrows():
            d = yf.download(row["ticker"], period="2d", progress=False)
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            sig = "🟢 強勢" if d["Open"].iloc[-1] > d["Close"].iloc[-2] else "🟡 觀察"
            live_data.append({"代號": row["代號"], "訊號": sig})
        st.dataframe(pd.DataFrame(live_data), use_container_width=True)

    # 轉折圖分析 (你成功的邏輯)
    st.write("---")
    st.subheader("🎯 轉折監測器")
    sel = st.selectbox("分析個股：", st.session_state["results"]["代號"].tolist())
    ticker = st.session_state["results"][st.session_state["results"]["代號"] == sel]["ticker"].values[0]
    
    df = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['5MA'], df['10MA'], df['20MA'] = df['Close'].rolling(5).mean(), df['Close'].rolling(10).mean(), df['Close'].rolling(20).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    
    # 均線看板
    l = df.iloc[-1]
    st.markdown(f"""<div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 15px; font-weight: bold;">
        <span style="color: #FF9800; margin-right: 20px;">5MA: {l['5MA']:.2f}</span>
        <span style="color: #2196F3; margin-right: 20px;">10MA: {l['10MA']:.2f}</span>
        <span style="color: #9C27B0;">20MA: {l['20MA']:.2f}</span></div>""", unsafe_allow_html=True)

    # 繪圖
    plots = [mpf.make_addplot(df[m], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])]
    fig, axlist = mpf.plot(df, type='candle', addplot=plots, returnfig=True, figsize=(10, 6), volume=True)
    ax = axlist[0]
    
    # 轉折標記 (你成功的邏輯)
    for g_id, group in df.groupby('State_Group'):
        if g_id <= 2: continue
        state = group['State'].iloc[0]
        idx = group['High'].idxmax() if state == 1 else group['Low'].idxmin()
        val = group['High'].max() if state == 1 else group['Low'].min()
        ax.text(df.index.get_loc(idx), val, "H" if state == 1 else "B", color='red' if state == 1 else 'green', 
                weight='bold', ha='center', bbox=dict(boxstyle="circle", fc="yellow", alpha=0.5))
    st.pyplot(fig)
