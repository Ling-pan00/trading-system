import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import datetime

# 設定頁面
st.set_page_config(page_title="三池完整監控系統", layout="wide")
st.title("📊 三池獨立交易監控系統 Pro ✖ 轉折波段連線")

# --- 初始化與選股邏輯 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

# 初始化 session_state
if "breakout" not in st.session_state:
    st.session_state.update({"breakout": pd.DataFrame(), "momentum": pd.DataFrame(), "pullback": pd.DataFrame()})

# --- 選股掃描 ---
if st.button("🚀 執行盤後選股"):
    tickers = [s["ticker"] for s in get_stock_list()][:100]
    data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
    res = []
    for t in tickers:
        try:
            df = data[t] if len(tickers) > 1 else data
            c, m5, m10, m20 = df["Close"].iloc[-1], df["Close"].rolling(5).mean().iloc[-1], df["Close"].rolling(10).mean().iloc[-1], df["Close"].rolling(20).mean().iloc[-1]
            s = (2 if c > m5 else 0) + (1 if m5 > m10 else 0) + (1 if m10 > m20 else 0)
            pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
            res.append({"代號": t.split('.')[0], "ticker": t, "分數": s, "池別": pool})
        except: continue
    df_res = pd.DataFrame(res)
    st.session_state["breakout"] = df_res[df_res["池別"] == "🚀 突破股"]
    st.session_state["momentum"] = df_res[df_res["池別"] == "🟡 動能股"]
    st.session_state["pullback"] = df_res[df_res["池別"] == "🧊 回檔股"]
    st.rerun()

# --- 顯示三池與盤中監控 ---
if not st.session_state["breakout"].empty:
    c1, c2, c3 = st.columns(3)
    for col, key in zip([c1, c2, c3], ["breakout", "momentum", "pullback"]):
        with col:
            st.subheader(key.capitalize())
            st.dataframe(st.session_state[key], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("📈 盤中即時監控")
    
    if st.button("🔄 更新盤中訊號"):
        all_df = pd.concat([st.session_state[k] for k in ["breakout", "momentum", "pullback"]])
        live = []
        data = yf.download(all_df["ticker"].tolist(), period="5d", group_by="ticker", progress=False)
        for _, row in all_df.iterrows():
            try:
                df = data[row["ticker"]] if len(all_df) > 1 else data
                sig = "🟢 強勢" if df["Open"].iloc[-1] >= df["Close"].iloc[-2] else "🟡 觀望"
                live.append({"代號": row["代號"], "訊號": sig})
            except: continue
        st.session_state["live_data"] = pd.DataFrame(live)
    
    if "live_data" in st.session_state:
        st.dataframe(st.session_state["live_data"], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("🎯 智慧轉折 K 線圖")
    all_stocks = pd.concat([st.session_state[k] for k in ["breakout", "momentum", "pullback"]])
    sel = st.selectbox("選擇股票看轉折圖", all_stocks["ticker"].unique())
    
    if sel:
        df_k = yf.download(sel, period="6mo", progress=False)
        df_k['5MA'] = df_k['Close'].rolling(5).mean()
        df_k = df_k.dropna().iloc[-90:]
        fig, ax = mpf.plot(df_k, type='candle', style='charles', addplot=mpf.make_addplot(df_k['5MA']), returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
else:
    st.info("💡 請先點擊『執行盤後選股』以載入資料。")
