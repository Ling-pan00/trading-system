import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime

# 設定頁面
st.set_page_config(page_title="四池量化 Pro v2.4", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.4 (完整整合版)")

# ==========================================
# 核心模組
# ==========================================
@st.cache_data(ttl=3600)
def get_clean_data(ticker):
    df = yf.download(ticker, period="3mo", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=['Close']).sort_index()

@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4:
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

def score(price, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    return (2 if price > ma5 else 0) + (1 if ma5 > ma10 else 0) + \
           (1 if ma10 > ma20 else 0) + (2 if vol > vol_ma5 else 0) + (1 if change_pct > 0 else 0)

def classify_pool(df, price, ma5, ma10, ma20, open_price, s):
    if df is None or len(df) < 30: return None
    ma20_up = df["ma20"].iloc[-1] > df["ma20"].iloc[-5]
    trend_align = (ma5 > ma10 > ma20)
    if ma20_up and trend_align and s >= 6: return "🔴 第四池"
    if ma20_up and trend_align and s >= 5: return "🔵 第三池"
    if ma20_up and trend_align and s >= 4: return "🟠 第二池"
    return None

# ==========================================
# 選股與顯示邏輯
# ==========================================
if st.button("🚀 執行完整盤後選股"):
    results = []
    tickers = [s["ticker"] for s in get_stock_list()]
    for t in tickers[:100]: # 可自行調整數量
        df = get_clean_data(t)
        if df is None or len(df) < 30: continue
        df = add_indicators(df)
        price, vol = df["Close"].iloc[-1], df["Volume"].iloc[-1]
        
        if vol / 1000 < 800: continue
        
        s = score(price, df["ma5"].iloc[-1], df["ma10"].iloc[-1], df["ma20"].iloc[-1], vol, df["vol_ma5"].iloc[-1], (price - df["Close"].iloc[-2])/df["Close"].iloc[-2])
        pool = classify_pool(df, price, df["ma5"].iloc[-1], df["ma10"].iloc[-1], df["ma20"].iloc[-1], df["Open"].iloc[-1], s)
        
        if pool:
            results.append({"代號": t, "池別": pool, "收盤": round(price, 2), "成交量(張)": int(vol/1000)})
    
    st.session_state["results"] = pd.DataFrame(results)
    st.rerun()

# 渲染結果
if "results" in st.session_state and not st.session_state["results"].empty:
    for p in ["🔴 第四池", "🔵 第三池", "🟠 第二池"]:
        pool_df = st.session_state["results"][st.session_state["results"]["池別"] == p]
        if not pool_df.empty:
            st.subheader(p)
            st.dataframe(pool_df, use_container_width=True)

    # 圖表區
    ticker_to_view = st.selectbox("選擇股票查看K線圖", st.session_state["results"]["代號"].unique())
    if st.button("繪製 K 線圖"):
        df_chart = get_clean_data(ticker_to_view)
        mc = mpf.make_marketcolors(up='red', down='green')
        fig, _ = mpf.plot(df_chart.tail(60), type='candle', style=mpf.make_mpf_style(marketcolors=mc), returnfig=True)
        st.pyplot(fig)
