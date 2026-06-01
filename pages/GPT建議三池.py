import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
from datetime import datetime, timedelta

# --- 頁面配置 ---
st.set_page_config(page_title="三池強力監控系統", layout="wide")
st.title("🚀 三池強力監控系統")

# --- 1. 資料處理與選股引擎 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

def get_zigzag_points(df):
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    points = []
    for g_id, group in df.groupby('State_Group'):
        if g_id <= 2: continue
        state = group['State'].iloc[0]
        if state == 1:
            idx = group['High'].idxmax()
            points.append((df.index.get_loc(idx), df.loc[idx, 'High'], "H"))
        else:
            idx = group['Low'].idxmin()
            points.append((df.index.get_loc(idx), df.loc[idx, 'Low'], "B"))
    return points

# --- 2. 介面與邏輯 ---
tickers = [s["ticker"] for s in get_stock_list()]
ticker_map = {s["ticker"]: s for s in get_stock_list()}

if st.button("🚀 執行強力選股"):
    results = []
    with st.spinner("掃描市場動能中..."):
        for t in tickers[:100]: # 限制數量以提升速度
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if len(df) < 20: continue
                c, ma5 = float(df["Close"].iloc[-1]), df["Close"].rolling(5).mean().iloc[-1]
                pct = float((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                s = (2 if c > ma5 else 0) + (2 if pct > 2 else 0)
                if s >= 3: results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t, "分數": s})
            except: continue
    st.session_state["results"] = pd.DataFrame(results)

if "results" in st.session_state and not st.session_state["results"].empty:
    sel = st.selectbox("分析個股：", st.session_state["results"]["代號"].tolist())
    ticker = st.session_state["results"][st.session_state["results"]["代號"] == sel]["ticker"].values[0]
    
    # 載入詳細 K 線數據
    df = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['5MA'], df['10MA'], df['20MA'] = df['Close'].rolling(5).mean(), df['Close'].rolling(10).mean(), df['Close'].rolling(20).mean()

    # --- 使用你成功的 HTML 看板排版 ---
    def get_ma_details(col):
        now, pre = df[col].iloc[-1], df[col].iloc[-2]
        return f"{now:.2f} {'▲' if now >= pre else '▼'}"

    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    # --- 繪圖區 ---
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df[m], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])]
    
    fig, axlist = mpf.plot(df, type='candle', style=style, addplot=plots, returnfig=True, figsize=(10, 6), volume=True)
    ax = axlist[0]
    
    # 繪製轉折線與點
    points = get_zigzag_points(df)
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    if len(x) > 1: ax.plot(x, y, color='black', alpha=0.4, linewidth=1, zorder=3)
    for x_pos, val, lbl in points:
        ax.text(x_pos, val, lbl, color='red' if lbl=="H" else 'green', weight='bold', ha='center', 
                bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))
    
    st.pyplot(fig)
