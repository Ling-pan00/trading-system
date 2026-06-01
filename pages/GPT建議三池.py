import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import datetime

# 設定頁面
st.set_page_config(page_title="三池強力監控系統", layout="wide")
st.title("🚀 三池強力監控系統 Pro ✖ 強勢動能篩選")

# --- 1. 股票池讀取 ---
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

# --- 2. 強勢動能評分系統 ---
def score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    if close > ma5: s += 2
    if ma5 > ma10: s += 1
    if ma10 > ma20: s += 1
    if vol > vol_ma5 * 1.5: s += 3  # 成交量爆量權重
    elif vol > vol_ma5: s += 1
    if change_pct > 2: s += 2       # 漲幅動能權重
    return s

def classify_pool(s):
    return "🚀 突破股" if s >= 7 else "🟡 動能股" if s >= 4 else "🧊 回檔股"

# --- 3. 盤後掃描 ---
if st.button("🚀 執行強力選股"):
    results = []
    with st.spinner("掃描市場動能中..."):
        for t in tickers[:150]: # 穩定掃描數量
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if df.empty or len(df) < 20: continue
                
                c = float(df["Close"].iloc[-1])
                pct = float((c - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                s = score(c, df["Close"].rolling(5).mean().iloc[-1], df["Close"].rolling(10).mean().iloc[-1], 
                          df["Close"].rolling(20).mean().iloc[-1], df["Volume"].iloc[-1], 
                          df["Volume"].rolling(5).mean().iloc[-1], pct)
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], 
                                "ticker": t, "分數": s, "池別": classify_pool(s), "漲幅": pct})
            except: continue
    
    if results:
        df = pd.DataFrame(results)
        for p, k in [("🚀 突破股", "breakout"), ("🟡 動能股", "momentum"), ("🧊 回檔股", "pullback")]:
            st.session_state[k] = df[df["池別"] == p].sort_values(["分數", "漲幅"], ascending=False).head(5)

# --- 4. 顯示結果與盤中監控 ---
if "breakout" in st.session_state:
    cols = st.columns(3)
    pools = {"🚀 突破股": "breakout", "🟡 動能股": "momentum", "🧊 回檔股": "pullback"}
    
    for i, (label, key) in enumerate(pools.items()):
        with cols[i]:
            st.subheader(label)
            st.dataframe(st.session_state[key][["代號", "名稱", "分數", "漲幅"]], use_container_width=True, hide_index=True)

    # --- 5. 轉折 K 線圖 (精確版) ---
    st.write("---")
    st.subheader("🎯 轉折監測器")
    pool_all = pd.concat([st.session_state[k] for k in pools.values()]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("選股分析：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    df_k = yf.download(ticker, period="6mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    df_k['5MA'] = df_k['Close'].rolling(5).mean()
    df_k['State'] = np.where(df_k['Close'] > df_k['5MA'], 1, -1)
    df_k['State_Group'] = (df_k['State'] != df_k['State'].shift()).cumsum()
    
    # 計算 Zigzag
    zigzag = []
    for g in df_k['State_Group'].unique():
        grp = df_k[df_k['State_Group'] == g]
        if grp['State'].iloc[0] == 1:
            idx = grp['High'].idxmax()
            zigzag.append((df_k.index.get_loc(idx), grp['High'].max(), "H"))
        else:
            idx = grp['Low'].idxmin()
            zigzag.append((df_k.index.get_loc(idx), grp['Low'].min(), "B"))

    fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(12, 8))
    ax = axlist[0]
    
    if len(zigzag) > 1:
        x, y, _ = zip(*zigzag[-15:])
        ax.plot(x, y, color='gray', linewidth=2, zorder=5)
        for i, (xi, yi, lbl) in enumerate(zigzag[-15:]):
            ax.text(xi, yi, lbl, color='red' if lbl=='H' else 'green', weight='bold', 
                    ha='center', va='bottom' if lbl=='H' else 'top', bbox=dict(fc="white", ec='gray', pad=1))
    
    st.pyplot(fig)
