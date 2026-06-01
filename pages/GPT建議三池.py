import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import datetime

# 設定頁面為寬螢幕版面
st.set_page_config(page_title="三池獨立監控系統", layout="wide")
st.title("📊 三池獨立交易監控系統 Pro ✖ 轉折波段連線")

# =========================
# 股票池初始化
# =========================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

# =========================
# 核心演算法
# =========================
def score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    if close > ma5: s += 2
    if ma5 > ma10: s += 1
    if ma10 > ma20: s += 1
    if vol > vol_ma5: s += 2
    if change_pct > 0: s += 1
    return s

def classify_pool(s):
    return "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"

def intraday_signal(open_p, close_y, low_y, high_y, vol, vol_y):
    if open_p >= close_y and vol >= vol_y * 0.7:
        return "🟢 BUY（追強）" if open_p > high_y else "🟢 BUY（回測）"
    return "🟡 WATCH"

# =========================
# 盤後掃描
# =========================
if st.button("🚀 盤後選股"):
    results = []
    with st.spinner("掃描中..."):
        # 限制數量以提升穩定性
        for t in tickers[:150]:
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if df.empty or len(df) < 20: continue
                
                c = df["Close"].iloc[-1]
                s = score(c, df["Close"].rolling(5).mean().iloc[-1], df["Close"].rolling(10).mean().iloc[-1], 
                          df["Close"].rolling(20).mean().iloc[-1], df["Volume"].iloc[-1], 
                          df["Volume"].rolling(5).mean().iloc[-1], (c - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], 
                                "ticker": t, "分數": s, "池別": classify_pool(s), "收盤": float(c)})
            except: continue
    
    if results:
        df = pd.DataFrame(results)
        st.session_state["breakout"] = df[df["池別"] == "🚀 突破股"].sort_values("分數", ascending=False).head(5)
        st.session_state["momentum"] = df[df["池別"] == "🟡 動能股"].sort_values("分數", ascending=False).head(5)
        st.session_state["pullback"] = df[df["池別"] == "🧊 回檔股"].sort_values("分數", ascending=False).head(5)

# =========================
# 顯示結果與盤中監控
# =========================
if "breakout" in st.session_state:
    cols = st.columns(3)
    pools = {"🚀 突破股": "breakout", "🟡 動能股": "momentum", "🧊 回檔股": "pullback"}
    
    for label, key in pools.items():
        with cols[list(pools.values()).index(key)]:
            st.subheader(label)
            st.dataframe(st.session_state[key][["代號", "名稱", "分數", "收盤"]], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("📈 盤中三池監控")
    if st.button("🔄 更新盤中訊號"):
        col1, col2, col3 = st.columns(3)
        for i, (label, key) in enumerate(pools.items()):
            live = []
            for _, row in st.session_state[key].iterrows():
                try:
                    df = yf.download(row["ticker"], period="5d", progress=False)
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    if df.empty: continue
                    sig = intraday_signal(float(df["Open"].iloc[-1]), float(df["Close"].iloc[-2]), 
                                          float(df["Low"].min()), float(df["High"].max()), 
                                          float(df["Volume"].iloc[-1]), float(df["Volume"].rolling(5).mean().iloc[-2]))
                    live.append({"代號": row["代號"], "訊號": sig})
                except: continue
            [col1, col2, col3][i].markdown(f"**{label}**")
            [col1, col2, col3][i].dataframe(pd.DataFrame(live), use_container_width=True, hide_index=True)

    # 轉折 K 線圖邏輯維持不變
    st.write("---")
    st.subheader("🎯 轉折 K 線圖")
    pool_all = pd.concat([st.session_state[k] for k in pools.values()]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("選擇股票：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    df_k = yf.download(ticker, period="6mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    df_k['5MA'] = df_k['Close'].rolling(5).mean()
    fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=mpf.make_addplot(df_k['5MA'].iloc[-90:], color='orange'), returnfig=True)
    st.pyplot(fig)
