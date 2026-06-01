import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import datetime

st.set_page_config(page_title="三池獨立監控系統", layout="wide")

st.title("📊 三池獨立交易監控系統 Pro ✖ 轉折波段連線")

@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
                stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

def calculate_score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    if close > ma5: s += 2
    if ma5 > ma10: s += 1
    if ma10 > ma20: s += 1
    if vol > vol_ma5: s += 2
    if change_pct > 0: s += 1
    return s

def get_pool_name(s):
    if s >= 5: return "🚀 突破股"
    if s >= 3: return "🟡 動能股"
    return "🧊 回檔股"

def check_signal(open_p, close_y, low_y, high_y, vol, vol_y):
    strong = open_p >= close_y
    hold = open_p >= low_y
    vol_ok = vol >= (vol_y * 0.7)
    breakout = open_p > high_y
    if strong and hold and vol_ok:
        return "🟢 BUY (追強)" if breakout else "🟢 BUY (回測)"
    if hold: return "🟡 WATCH"
    return "🔴 NO"

if st.button("🚀 執行盤後選股掃描"):
    results = []
    batch_size = 100
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        data = yf.download(batch, period="3mo", group_by="ticker", progress=False)
        for t in batch:
            try:
                df = data[t] if len(batch) > 1 else data
                if len(df) < 20: continue
                c = df["Close"].iloc[-1]
                v = df["Volume"].iloc[-1]
                ma5 = df["Close"].rolling(5).mean().iloc[-1]
                ma10 = df["Close"].rolling(10).mean().iloc[-1]
                ma20 = df["Close"].rolling(20).mean().iloc[-1]
                vma5 = df["Volume"].rolling(5).mean().iloc[-1]
                pct = (c - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
                s = calculate_score(c, ma5, ma10, ma20, v, vma5, pct)
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t, "分數": s, "池別": get_pool_name(s)})
            except: continue
    
    df_res = pd.DataFrame(results)
    st.session_state["breakout"] = df_res[df_res["池別"] == "🚀 突破股"].head(5)
    st.session_state["momentum"] = df_res[df_res["池別"] == "🟡 動能股"].head(5)
    st.session_state["pullback"] = df_res[df_res["池別"] == "🧊 回檔股"].head(5)

if "breakout" in st.session_state:
    cols = st.columns(3)
    keys = ["breakout", "momentum", "pullback"]
    for i, col in enumerate(cols):
        with col:
            st.subheader(keys[i].capitalize())
            st.dataframe(st.session_state[keys[i]], use_container_width=True)

    st.write("---")
    st.subheader("📈 盤中即時監控")
    if st.button("🔄 更新盤中訊號"):
        def fetch_live(df):
            live = []
            if df.empty: return pd.DataFrame()
            data = yf.download(df["ticker"].tolist(), period="5d", group_by="ticker", progress=False)
            for _, row in df.iterrows():
                try:
                    d = data[row["ticker"]] if len(df) > 1 else data
                    sig = check_signal(d["Open"].iloc[-1], d["Close"].iloc[-2], d["Low"].iloc[-2], d["High"].iloc[-2], d["Volume"].iloc[-1], d["Volume"].rolling(5).mean().iloc[-1])
                    live.append({"代號": row["代號"], "訊號": sig})
                except: continue
            return pd.DataFrame(live)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.dataframe(fetch_live(st.session_state["breakout"]))
        with c2: st.dataframe(fetch_live(st.session_state["momentum"]))
        with c3: st.dataframe(fetch_live(st.session_state["pullback"]))
