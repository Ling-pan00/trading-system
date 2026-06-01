import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

# --- 設定 ---
st.set_page_config(page_title="三池強力監控系統 Pro", layout="wide")
st.title("🚀 三池強力監控系統 Pro")

# --- 1. 資料處理函式 ---
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
    df['Change'] = df['State'] != df['State'].shift()
    points = []
    for i in range(20, len(df)):
        if df['Change'].iloc[i]:
            segment = df.iloc[max(0, i-20):i]
            if df['State'].iloc[i] == -1:
                idx = segment['High'].idxmax()
                points.append((idx, segment['High'].max(), "H"))
            else:
                idx = segment['Low'].idxmin()
                points.append((idx, segment['Low'].min(), "B"))
    return points

# --- 2. 核心邏輯區 ---
if "breakout" not in st.session_state: st.session_state["breakout"] = pd.DataFrame()
tickers = [s["ticker"] for s in get_stock_list()]
ticker_map = {s["ticker"]: s for s in get_stock_list()}

if st.button("🚀 執行強力選股"):
    results = []
    with st.spinner("掃描市場動能中..."):
        for t in tickers[:150]:
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if len(df) < 20: continue
                c, ma5 = float(df["Close"].iloc[-1]), df["Close"].rolling(5).mean().iloc[-1]
                vol_ma5, pct = df["Volume"].rolling(5).mean().iloc[-1], float((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                s = (2 if c > ma5 else 0) + (3 if df["Volume"].iloc[-1] > vol_ma5 * 1.5 else 1) + (2 if pct > 2 else 0)
                pool = "🚀 突破股" if s >= 7 else "🟡 動能股" if s >= 4 else "🧊 回檔股"
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t, "分數": s, "池別": pool})
            except: continue
    if results:
        df = pd.DataFrame(results)
        for p, k in [("🚀 突破股", "breakout"), ("🟡 動能股", "momentum"), ("🧊 回檔股", "pullback")]:
            st.session_state[k] = df[df["池別"] == p].sort_values("分數", ascending=False).head(5)

# --- 3. 完整介面與監控 ---
if not st.session_state["breakout"].empty:
    pools = {"🚀 突破股": "breakout", "🟡 動能股": "momentum", "🧊 回檔股": "pullback"}
    
    cols = st.columns(3)
    for i, (label, key) in enumerate(pools.items()):
        cols[i].subheader(label)
        cols[i].dataframe(st.session_state[key][["代號", "名稱", "分數"]], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("📈 盤中動能監控")
    if st.button("🔄 更新訊號"):
        for label, key in pools.items():
            st.markdown(f"**{label}**")
            live = []
            for _, row in st.session_state[key].iterrows():
                try:
                    d = yf.download(row["ticker"], period="5d", progress=False)
                    if d.empty: continue
                    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                    sig = "🟢 BUY" if d["Open"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 WATCH"
                    live.append({"代號": row["代號"], "訊號": sig})
                except: continue
            if live: st.dataframe(pd.DataFrame(live), use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("🎯 轉折監測器")
    pool_all = pd.concat([st.session_state[k] for k in pools.values()]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("分析個股：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    df_k = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    df_k['5MA'], df_k['10MA'], df_k['20MA'] = df_k['Close'].rolling(5).mean(), df_k['Close'].rolling(10).mean(), df_k['Close'].rolling(20
