import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

# --- 頁面配置 ---
st.set_page_config(page_title="三池強力監控系統 Pro", layout="wide")
st.title("🚀 三池強力監控系統 Pro")

# --- 1. 資料處理與選股邏輯 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

tickers = [s["ticker"] for s in get_stock_list()]
ticker_map = {s["ticker"]: s for s in get_stock_list()}

def get_zigzag_points(df):
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['Change'] = df['State'] != df['State'].shift()
    points = []
    for i in range(20, len(df)):
        if df['Change'].iloc[i]:
            segment = df.iloc[max(0, i-20):i]
            if df['State'].iloc[i] == -1: # 跌破找高
                idx = segment['High'].idxmax()
                points.append((idx, segment['High'].max(), "H"))
            else: # 站回找低
                idx = segment['Low'].idxmin()
                points.append((idx, segment['Low'].min(), "B"))
    return points

# --- 2. 盤後強力選股 ---
if st.button("🚀 執行強力選股"):
    results = []
    with st.spinner("掃描市場動能中..."):
        for t in tickers[:150]:
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if df.empty or len(df) < 20: continue
                c = float(df["Close"].iloc[-1])
                ma5 = df["Close"].rolling(5).mean().iloc[-1]
                vol_ma5 = df["Volume"].rolling(5).mean().iloc[-1]
                pct = float((c - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                s = (2 if c > ma5 else 0) + (3 if df["Volume"].iloc[-1] > vol_ma5 * 1.5 else 1) + (2 if pct > 2 else 0)
                pool = "🚀 突破股" if s >= 7 else "🟡 動能股" if s >= 4 else "🧊 回檔股"
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t, "分數": s, "池別": pool, "漲幅": pct})
            except: continue
    if results:
        df = pd.DataFrame(results)
        for p, k in [("🚀 突破股", "breakout"), ("🟡 動能股", "momentum"), ("🧊 回檔股", "pullback")]:
            st.session_state[k] = df[df["池別"] == p].sort_values(["分數", "漲幅"], ascending=False).head(5)

# --- 3. 顯示區塊 ---
if "breakout" in st.session_state:
    cols = st.columns(3)
    pools = {"🚀 突破股": "breakout", "🟡 動能股": "momentum", "🧊 回檔股": "pullback"}
    for i, (label, key) in enumerate(pools.items()):
        with cols[i]:
            st.subheader(label)
            st.dataframe(st.session_state[key][["代號", "名稱", "分數", "漲幅"]], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("📈 盤中動能監控")
    if st.button("🔄 更新訊號"):
        for label, key in pools.items():
            st.markdown(f"**{label}**")
            live = []
            for _, row in st.session_state[key].iterrows():
                d = yf.download(row["ticker"], period="5d", progress=False)
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                sig = "🟢 BUY" if d["Open"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 WATCH"
                live.append({"代號": row["代號"], "訊號": sig})
            st.dataframe(pd.DataFrame(live), use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("🎯 轉折監測器 (近 3 個月)")
    pool_all = pd.concat([st.session_state[k] for k in pools.values()]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("選股分析：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    df_k = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    df_k['5MA'], df_k['10MA'], df_k['20MA'] = df_k['Close'].rolling(5).mean(), df_k['Close'].rolling(10).mean(), df_k['Close'].rolling(20).mean()
    
    # 指標看板
    last = df_k.iloc[-1]
    prev = df_k.iloc[-2]
    c1, c2, c3 = st.columns(3)
    c1.metric("5MA", f"{last['5MA']:.2f}", "▲" if last['5MA'] > prev['5MA'] else "▼")
    c2.metric("10MA", f"{last['10MA']:.2f}", "▲" if last['10MA'] > prev['10MA'] else "▼")
    c3.metric("20MA", f"{last['20MA']:.2f}", "▲" if last['20MA'] > prev['20MA'] else "▼")
    
    # 繪圖
    fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(12, 8),
                           addplot=[mpf.make_addplot(df_k[['5MA', '10MA', '20MA']].iloc[-90:], color=dict(zip(['5MA','10MA','20MA'],['orange','blue','purple'])))])
    ax = axlist[0]
    
    points = get_zigzag_points(df_k)
    for idx, val, lbl in points:
        if idx in df_k.iloc[-90:].index:
            x_pos = df_k.index.get_loc(idx)
            ax.annotate(lbl, (x_pos, val), xytext=(0, 15 if lbl=='H' else -15), textcoords='offset points',
                        ha='center', color='red' if lbl=='H' else 'green', weight='bold',
                        bbox=dict(fc="white", ec='red' if lbl=='H' else 'green', pad=1))
    st.pyplot(fig)
