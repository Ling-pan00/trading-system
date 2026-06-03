import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

# --- 設定 ---
st.set_page_config(page_title="三池強力監控系統 Pro", layout="wide")
st.title("🚀 三池強力監控系統 Pro")

# --- 1. 核心資料處理函式 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

def get_zigzag_points(df):
    df_c = df.copy()
    df_c['5MA'] = df_c['Close'].rolling(5).mean()
    df_c['State'] = np.where(df_c['Close'] > df_c['5MA'], 1, -1)
    df_c['Change'] = df_c['State'] != df_c['State'].shift()
    points = []
    for i in range(20, len(df_c)):
        if df_c['Change'].iloc[i]:
            segment = df_c.iloc[max(0, i-20):i]
            idx = segment['High'].idxmax() if df_c['State'].iloc[i] == -1 else segment['Low'].idxmin()
            lbl = "H" if df_c['State'].iloc[i] == -1 else "B"
            points.append((idx, df_c.loc[idx, 'High'] if lbl=="H" else df_c.loc[idx, 'Low'], lbl))
    return points

# --- 2. 核心邏輯區 ---
if "breakout" not in st.session_state: st.session_state.update({"breakout":pd.DataFrame(), "momentum":pd.DataFrame(), "pullback":pd.DataFrame()})
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
pools = {"🚀 突破股": "breakout", "🟡 動能股": "momentum", "🧊 回檔股": "pullback"}
if any(not st.session_state[k].empty for k in pools.values()):
    # 列表展示
    cols = st.columns(3)
    for i, (label, key) in enumerate(pools.items()):
        cols[i].subheader(label)
        if not st.session_state[key].empty: cols[i].dataframe(st.session_state[key][["代號", "名稱", "分數"]], use_container_width=True, hide_index=True)
    
    # 盤中動能監控
    st.write("---")
    if st.button("🔄 更新監控訊號"):
        for label, key in pools.items():
            if st.session_state[key].empty: continue
            st.write(f"**{label}**"); live = []
            for _, row in st.session_state[key].iterrows():
                try:
                    d = yf.download(row["ticker"], period="5d", progress=False)
                    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                    sig = "🟢 BUY" if d["Open"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 WATCH"
                    live.append({"代號": row["代號"], "訊號": sig})
                except: continue
            if live: st.dataframe(pd.DataFrame(live), use_container_width=True, hide_index=True)

    # 轉折圖
    st.write("---")
    st.subheader("🎯 轉折監測器")
    pool_all = pd.concat([st.session_state[k] for k in pools.values() if not st.session_state[k].empty]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("分析個股：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    df_k = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    df_k['5MA'], df_k['10MA'], df_k['20MA'] = df_k['Close'].rolling(5).mean(), df_k['Close'].rolling(10).mean(), df_k['Close'].rolling(20).mean()
    
    # HTML 美觀看板
    l, p = df_k.iloc[-1], df_k.iloc[-2]
    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {l['5MA']:.2f} {'▲' if l['5MA'] > p['5MA'] else '▼'}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {l['10MA']:.2f} {'▲' if l['10MA'] > p['10MA'] else '▼'}</span>
            <span style="color: #9C27B0;">20MA: {l['20MA']:.2f} {'▲' if l['20MA'] > p['20MA'] else '▼'}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # 繪圖
    fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                           addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
    ax = axlist[0]
    for idx, val, lbl in get_zigzag_points(df_k):
        if idx in df_k.iloc[-90:].index:
            ax.annotate(lbl, (df_k.index.get_loc(idx), val), ha='center', color='red' if lbl=='H' else 'green', weight='bold', bbox=dict(fc="yellow", alpha=0.5))
    st.pyplot(fig)


