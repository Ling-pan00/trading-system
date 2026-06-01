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
# 股票池
# =========================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
                stocks.append({
                    "code": code,
                    "name": info.name,
                    "ticker": ticker
                })
    return stocks

stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

st.write(f"📦 股票數：{len(tickers)}")

# =========================
# 評分與訊號邏輯
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
    strong = open_p >= close_y
    hold = open_p >= low_y
    vol_ok = vol >= vol_y * 0.7
    breakout = open_p > high_y
    if strong and hold and vol_ok:
        return "🟢 BUY（追強）" if breakout else "🟢 BUY（回測）"
    if hold: return "🟡 WATCH"
    return "🔴 NO"

# =========================
# 盤後掃描
# =========================
if st.button("🚀 盤後選股"):
    results = []
    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    status = st.empty()

    for i in range(total_batches):
        batch = tickers[i*batch_size:(i+1)*batch_size]
        status.text(f"📥 正在掃描... {i+1}/{total_batches}")
        try:
            data = yf.download(tickers=batch, period="3mo", interval="1d", group_by="ticker", progress=False)
            for t in batch:
                try:
                    df_s = data[t] if len(batch) > 1 else data
                    if df_s.empty or len(df_s) < 20: continue
                    if isinstance(df_s.columns, pd.MultiIndex): df_s.columns = df_s.columns.get_level_values(0)
                    
                    close, volume = df_s["Close"], df_s["Volume"]
                    ma5, ma10, ma20 = close.rolling(5).mean().iloc[-1], close.rolling(10).mean().iloc[-1], close.rolling(20).mean().iloc[-1]
                    vol_ma5 = volume.rolling(5).mean().iloc[-1]
                    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

                    s = score(close.iloc[-1], ma5, ma10, ma20, volume.iloc[-1], vol_ma5, change_pct)
                    results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t, "分數": s, "池別": classify_pool(s), "收盤": float(close.iloc[-1])})
                except: continue
        except: continue
        progress.progress((i+1)/total_batches)

    status.text("✅ 完成")
    if results:
        df = pd.DataFrame(results)
        st.session_state["breakout"] = df[df["池別"] == "🚀 突破股"].sort_values("分數", ascending=False).head(5)
        st.session_state["momentum"] = df[df["池別"] == "🟡 動能股"].sort_values("分數", ascending=False).head(5)
        st.session_state["pullback"] = df[df["池別"] == "🧊 回檔股"].sort_values("分數", ascending=False).head(5)

# =========================
# 顯示結果與盤中監控
# =========================
if "
