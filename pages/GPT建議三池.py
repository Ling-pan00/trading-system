import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import datetime

# 設定頁面為寬螢幕版面
st.set_page_config(page_title="三池強力監控系統", layout="wide")
st.title("🚀 三池強力監控系統 Pro ✖ 強勢動能篩選")

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
# 進化版：強勢動能評分系統
# =========================
def score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    # 1. 趨勢加分 (多頭排列)
    if close > ma5: s += 2
    if ma5 > ma10: s += 1
    if ma10 > ma20: s += 1
    
    # 2. 強勢量能分：若成交量爆出 1.5 倍以上均量，代表主力進場，給予高權重
    if vol > vol_ma5 * 1.5: s += 3
    elif vol > vol_ma5: s += 1
    
    # 3. 爆發力加分：漲幅超過 2% 的股票通常具有慣性，額外加分
    if change_pct > 2: s += 2
    
    return s

def classify_pool(s):
    return "🚀 突破股" if s >= 7 else "🟡 動能股" if s >= 4 else "🧊 回檔股"

def intraday_signal(open_p, close_y, low_y, high_y, vol, vol_y):
    if open_p >= close_y and vol >= vol_y * 0.7:
        return "🟢 BUY（追強）" if open_p > high_y else "🟢 BUY（回測）"
    return "🟡 WATCH"

# =========================
# 盤後掃描 (加入動能篩選)
# =========================
if st.button("🚀 執行強力選股"):
    results = []
    with st.spinner("正在進行強勢標的掃描..."):
        for t in tickers[:200]: # 掃描前 200 檔增加涵蓋率
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if df.empty or len(df) < 20: continue
                
                c = df["Close"].iloc[-1]
                pct = (c - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100
                s = score(c, df["Close"].rolling(5).mean().iloc[-1], df["Close"].rolling(10).mean().iloc[-1], 
                          df["Close"].rolling(20).mean().iloc[-1], df["Volume"].iloc[-1], 
                          df["Volume"].rolling(5).mean().iloc[-1], pct)
                
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], 
                                "ticker": t, "分數": s, "池別": classify_pool(s), "收盤": float(c), "漲幅": float(pct)})
            except: continue
    
    if results:
        df = pd.DataFrame(results)
        # 加入「漲幅」作為第二排序條件，確保同分時選出波動更大的強勢股
        st.session_state["breakout"] = df[df["池別"] == "🚀 突破股"].sort_values(["分數", "漲幅"], ascending=False).head(5)
        st.session_state["momentum"] = df[df["池別"] == "🟡 動能股"].sort_values(["分數", "漲幅"], ascending=False).head(5)
        st.session_state["pullback"] = df[df["池別"] == "🧊 回檔股"].sort_values(["分數", "漲幅"], ascending=False).head(5)

# =========================
# 顯示介面
# =========================
if "breakout" in st.session_state:
    cols = st.columns(3)
    pools = {"🚀 突破股": "breakout", "🟡 動能股": "momentum", "🧊 回檔股": "pullback"}
    
    for i, (label, key) in enumerate(pools.items()):
        with cols[i]:
            st.subheader(label)
            st.dataframe(st.session_state[key][["代號", "名稱", "分數", "漲幅"]], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("📈 盤中動能監控")
    if st.button("🔄 更新盤中動能"):
        for label, key in pools.items():
            st.markdown(f"**{label}**")
            live = []
            for _, row in st.session_state[key].iterrows():
                try:
                    df = yf.download(row["ticker"], period="5d", progress=False)
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    sig = intraday_signal(float(df["Open"].iloc[-1]), float(df["Close"].iloc[-2]), 
                                          float(df["Low"].min()), float(df["High"].max()), 
                                          float(df["Volume"].iloc[-1]), float(df["Volume"].rolling(5).mean().iloc[-2]))
                    live.append({"代號": row["代號"], "訊號": sig})
                except: continue
            st.dataframe(pd.DataFrame(live), use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("🎯 轉折監測器")
    pool_all = pd.concat([st.session_state[k] for k in pools.values()]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("選股分析：", pool_all["代號"].tolist())
    
    # K 線繪圖 (略)
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    df_k = yf.download(ticker, period="6mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True)
    st.pyplot(fig)
