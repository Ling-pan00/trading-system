import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

st.set_page_config(page_title="三池完整監控系統", layout="wide")
st.title("📊 三池完整交易監控系統 Pro ✖ 轉折波段連線")

# --- 初始化與選股邏輯 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4:
            stocks.append({"code": code, "name": info.name, "ticker": f"{code}.TW" if info.market == "上市" else f"{code}.TWO"})
    return stocks

if "initialized" not in st.session_state:
    st.session_state.update({"breakout": None, "momentum": None, "pullback": None})

if st.button("🚀 執行盤後選股"):
    tickers = [s["ticker"] for s in get_stock_list()][:100]
    data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
    res = []
    for t in tickers:
        try:
            df = data[t] if len(tickers) > 1 else data
            c, m5, m10, m20 = df["Close"].iloc[-1], df["Close"].rolling(5).mean().iloc[-1], df["Close"].rolling(10).mean().iloc[-1], df["Close"].rolling(20).mean().iloc[-1]
            s = (2 if c > m5 else 0) + (1 if m5 > m10 else 0) + (1 if m10 > m20 else 0)
            res.append({"ticker": t, "分數": s, "池別": "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"})
        except: continue
    df_res = pd.DataFrame(res)
    st.session_state["breakout"] = df_res[df_res["池別"] == "🚀 突破股"]
    st.session_state["momentum"] = df_res[df_res["池別"] == "🟡 動能股"]
    st.session_state["pullback"] = df_res[df_res["池別"] == "🧊 回檔股"]

# --- 顯示介面 ---
if st.session_state["breakout"] is not None:
    c1, c2, c3 = st.columns(3)
    for col, key in zip([c1, c2, c3], ["breakout", "momentum", "pullback"]):
        with col:
            st.subheader(key.capitalize())
            st.dataframe(st.session_state[key], use_container_width=True)

    st.write("---")
    # 盤中監控
    if st.button("🔄 更新盤中"):
        st.session_state["live"] = "更新中..." # 這裡可放入您的監控邏輯
    
    # 轉折圖
    all_stocks = pd.concat([st.session_state[k] for k in ["breakout", "momentum", "pullback"]])
    sel = st.selectbox("選擇股票看轉折圖", all_stocks["ticker"].unique())
    
    df_k = yf.download(sel, period="6mo", progress=False)
    # 轉折標記邏輯 (ZigZag)
    df_k['5MA'] = df_k['Close'].rolling(5).mean()
    df_k = df_k.dropna().iloc[-90:]
    
    # 繪圖
    fig, ax = mpf.plot(df_k, type='candle', addplot=mpf.make_addplot(df_k['5MA']), returnfig=True)
    st.pyplot(fig)
