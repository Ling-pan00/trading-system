import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

st.set_page_config(page_title="四池量化 Pro v2.4", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.4 (完整修正版)")

# ==========================================
# 核心修正：資料獲取與清洗模組
# ==========================================
@st.cache_data(ttl=3600)
def get_clean_data(ticker):
    """確保取得正確日期且資料完整之收盤數據"""
    df = yf.download(ticker, period="3mo", interval="1d", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna(subset=['Close']).sort_index()
    return df

@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4:
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

# ==========================================
# 策略指標與四池分類邏輯
# ==========================================
def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

def score(price, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = (2 if price > ma5 else 0) + (1 if ma5 > ma10 else 0) + (1 if ma10 > ma20 else 0) + \
        (2 if vol > vol_ma5 else 0) + (1 if change_pct > 0 else 0)
    return s

def classify_pool(df, price, ma5, ma10, ma20, open_price, s):
    if df is None or len(df) < 30: return None
    ma20_up = df["ma20"].iloc[-1] > df["ma20"].iloc[-5]
    trend_align = (ma5 > ma10 > ma20)
    if ma20_up and trend_align and s >= 6: return "🔴 第四池"
    if ma20_up and trend_align and s >= 5: return "🔵 第三池"
    if ma20_up and trend_align and s >= 4: return "🟠 第二池"
    return None

def trade_levels(price, ma5, ma10, pool):
    if pool == "🔴 第四池": stop, target = ma10, price * 1.25
    elif pool == "🔵 第三池": stop, target = ma5, price * 1.20
    elif pool == "🟠 第二池": stop, target = ma5, price * 1.15
    else: stop, target = ma10, price * 1.10
    return round(price, 2), round(stop, 2), round(target, 2)

# ==========================================
# 繪圖模組
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    df = get_clean_data(ticker_code)
    st.subheader(f"📈 {stock_name} ({ticker_code})")
    mc = mpf.make_marketcolors(up='red', down='green', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc)
    fig, _ = mpf.plot(df.tail(60), type='candle', style=style, volume=True, returnfig=True)
    st.pyplot(fig)

# ==========================================
# 主程式：盤後選股與顯示
# ==========================================
if st.button("🚀 執行完整盤後選股"):
    results = []
    tickers = [s["ticker"] for s in get_stock_list()]
    progress = st.progress(0)
    for i, t in enumerate(tickers[:100]):
        df = get_clean_data(t)
        if len(df) < 30: continue
        df = add_indicators(df)
        price, vol = df["Close"].iloc[-1], df["Volume"].iloc[-1]
        if vol / 1000 < 800: continue
        
        s = score(price, df["ma5"].iloc[-1], df["ma10"].iloc[-1], df["ma20"].iloc[-1], vol, df["vol_ma5"].iloc[-1], (price - df["Close"].iloc[-2])/df["Close"].iloc[-2])
        pool = classify_pool(df, price, df["ma5"].iloc[-1], df["ma10"].iloc[-1], df["ma20"].iloc[-1], df["Open"].iloc[-1], s)
        
        if pool:
            entry, stop, target = trade_levels(price, df["ma5"].iloc[-1], df["ma10"].iloc[-1], pool)
            results.append({"代號": t, "池別": pool, "收盤": round(price, 2), "停損": stop, "目標": target})
        progress.progress((i + 1) / 100)
    st.session_state["results"] = pd.DataFrame(results)
    st.rerun()

if "results" in st.session_state and not st.session_state["results"].empty:
    for p in ["🔴 第四池", "🔵 第三池", "🟠 第二池"]:
        pool_df = st.session_state["results"][st.session_state["results"]["池別"] == p]
        if not pool_df.empty:
            st.subheader(p)
            st.dataframe(pool_df, use_container_width=True)
    
    view_t = st.selectbox("選擇股票查看K線圖", st.session_state["results"]["代號"].unique())
    if st.button("繪製 K 線圖"):
        draw_zigzag_chart(view_t, "Target")
