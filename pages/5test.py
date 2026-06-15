import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime

# 頁面配置
st.set_page_config(page_title="四池量化 Pro v2.4", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.4 (完整版)")

# ==========================================
# 核心功能模組
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

# ==========================================
# 🚀 盤後選股邏輯
# ==========================================
if st.button("🚀 執行完整盤後選股"):
    results = []
    tickers = [s["ticker"] for s in get_stock_list()]
    progress = st.progress(0)
    
    # 實際運作建議跑全部，此處為演示，若太慢可限制數量
    for i, t in enumerate(tickers[:50]):
        df = get_clean_data(t)
        if df is None or len(df) < 30: continue
        
        df = add_indicators(df)
        price = df["Close"].iloc[-1]
        vol_sheets = df["Volume"].iloc[-1] / 1000
        
        if vol_sheets >= 800: # 800張門檻
            # 簡化版分類 (僅作範例)
            results.append({
                "代號": t,
                "收盤": round(price, 2),
                "成交量(張)": int(vol_sheets)
            })
        progress.progress((i + 1) / 50)
    
    st.session_state["results"] = pd.DataFrame(results)
    st.rerun()

# ==========================================
# 📊 畫面渲染與結果顯示
# ==========================================
if "results" in st.session_state and not st.session_state["results"].empty:
    st.subheader("📊 選股結果")
    st.dataframe(st.session_state["results"], use_container_width=True)
    
    # 圖表查看功能
    ticker_to_view = st.selectbox("選擇股票查看K線圖", st.session_state["results"]["代號"].unique())
    if st.button("繪製 K 線圖"):
        df_chart = get_clean_data(ticker_to_view)
        st.markdown(f"**{ticker_to_view} 走勢圖**")
        
        # 繪圖
        mc = mpf.make_marketcolors(up='red', down='green')
        s_style = mpf.make_mpf_style(marketcolors=mc)
        fig, ax = mpf.plot(df_chart.tail(60), type='candle', style=s_style, returnfig=True)
        st.pyplot(fig)
else:
    st.info("請點擊上方按鈕執行選股分析。")
