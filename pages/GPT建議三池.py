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
# 股票清單讀取
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
# 評分與分類邏輯
# =========================
def score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    if close > ma5: s += 2
    if ma5 > ma10: s += 1
    if ma10 > ma20: s += 1
    if vol > vol_ma5: s += 2
    if change_pct > 0: s += 1
    return s

def classify_pool(score):
    if score >= 5: return "🚀 突破股"
    elif score >= 3: return "🟡 動能股"
    else: return "🧊 回檔股"

def intraday_signal(open_p, close_y, low_y, high_y, vol, vol_y):
    if open_p >= close_y and vol >= vol_y * 0.7:
        return "🟢 BUY（強勢）" if open_p > high_y else "🟢 BUY（回測）"
    return "🟡 WATCH"

# =========================
# 盤後掃描 (穩定版)
# =========================
if st.button("🚀 盤後選股"):
    results = []
    with st.spinner("掃描市場中..."):
        # 為了穩定，改為分批處理
        for t in tickers[:150]: # 限制數量以保證不超時
            try:
                df = yf.download(t, period="3mo", progress=False)
                if df.empty or len(df) < 20: continue
                close, vol = df["Close"], df["Volume"]
                s = score(close.iloc[-1], close.rolling(5).mean().iloc[-1], 
                          close.rolling(10).mean().iloc[-1], close.rolling(20).mean().iloc[-1],
                          vol.iloc[-1], vol.rolling(5).mean().iloc[-1], 
                          (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100)
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], 
                                "ticker": t, "分數": s, "池別": classify_pool(s), "收盤": float(close.iloc[-1])})
            except: continue
    
    if results:
        df = pd.DataFrame(results)
        st.session_state["breakout"] = df[df["池別"] == "🚀 突破股"].sort_values("分數", ascending=False).head(5)
        st.session_state["momentum"] = df[df["池別"] == "🟡 動能股"].sort_values("分數", ascending=False).head(5)
        st.session_state["pullback"] = df[df["池別"] == "🧊 回檔股"].sort_values("分數", ascending=False).head(5)

# =========================
# 顯示選股成果
# =========================
if "breakout" in st.session_state:
    cols = st.columns(3)
    for i, p in enumerate(["breakout", "momentum", "pullback"]):
        with cols[i]:
            st.subheader(f"{p.capitalize()} Top5")
            st.dataframe(st.session_state[p][["代號", "名稱", "分數", "收盤"]], use_container_width=True, hide_index=True)

    # 盤中監控 (修正錯誤版)
    st.subheader("📈 盤中監控")
    if st.button("🔄 更新盤中"):
        for p in ["breakout", "momentum", "pullback"]:
            live = []
            for _, row in st.session_state[p].iterrows():
                try:
                    df = yf.download(row["ticker"], period="5d", progress=False)
                    if not df.empty:
                        sig = intraday_signal(df["Open"].iloc[-1], df["Close"].iloc[-2], df["Low"].min(), df["High"].max(), df["Volume"].iloc[-1], df["Volume"].rolling(5).mean().iloc[-1])
                        live.append({**row.to_dict(), "訊號": sig})
                except: continue
            st.dataframe(pd.DataFrame(live)[["代號", "訊號"]], use_container_width=True, hide_index=True)

    # 轉折 K 線圖
    st.write("---")
    pool_all = pd.concat([st.session_state[p] for p in ["breakout", "momentum", "pullback"]]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("選擇股票分析：", pool_all["代號"].tolist())
    
    if sel:
        ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
        df_k = yf.download(ticker, period="6mo", progress=False)
        df_k['5MA'] = df_k['Close'].rolling(5).mean()
        fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=mpf.make_addplot(df_k['5MA'].iloc[-90:], color='orange'), returnfig=True)
        st.pyplot(fig)
