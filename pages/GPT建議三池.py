import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

# 設定頁面
st.set_page_config(page_title="三池獨立監控系統", layout="wide")
st.title("📊 三池獨立交易監控系統 Pro")

# 1. 取得股票池 (快取處理)
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

# 2. 初始化應用狀態
if "results" not in st.session_state:
    st.session_state["results"] = None
if "monitor_data" not in st.session_state:
    st.session_state["monitor_data"] = None

# 3. 盤後選股功能
if st.button("🚀 執行盤後選股掃描"):
    with st.spinner('正在從 Yahoo Finance 抓取資料...'):
        tickers = [s["ticker"] for s in get_stock_list()]
        # 為演示效能，預設取前 50 檔
        batch = tickers[:50]
        data = yf.download(batch, period="3mo", group_by="ticker", progress=False)
        
        results = []
        for t in batch:
            try:
                df = data[t] if len(batch) > 1 else data
                if len(df) < 20: continue
                # 簡單邏輯：收盤大於 5MA
                c = df["Close"].iloc[-1]
                ma5 = df["Close"].rolling(5).mean().iloc[-1]
                if c > ma5:
                    results.append({"代號": t.split('.')[0], "ticker": t, "收盤": float(c), "狀態": "突破"})
            except: continue
        st.session_state["results"] = pd.DataFrame(results)

# 4. 顯示選股成果
if st.session_state["results"] is not None:
    st.subheader("📋 選股結果")
    st.dataframe(st.session_state["results"], use_container_width=True)

    st.write("---")
    st.subheader("📈 盤中即時監控")
    
    # 5. 盤中監控功能
    if st.button("🔄 更新盤中訊號"):
        df_pool = st.session_state["results"]
        live_list = []
        data = yf.download(df_pool["ticker"].tolist(), period="5d", group_by="ticker", progress=False)
        
        for _, row in df_pool.iterrows():
            try:
                d = data[row["ticker"]] if len(df_pool) > 1 else data
                # 簡單盤中訊號：現價是否大於昨收
                if d["Close"].iloc[-1] > d["Close"].iloc[-2]:
                    live_list.append({"代號": row["代號"], "訊號": "🟢 強勢"})
                else:
                    live_list.append({"代號": row["代號"], "訊號": "🟡 觀望"})
            except: continue
        st.session_state["monitor_data"] = pd.DataFrame(live_list)

    # 顯示持久化的盤中監控表
    if st.session_state["monitor_data"] is not None:
        st.dataframe(st.session_state["monitor_data"], use_container_width=True)
else:
    st.info("💡 請先點擊『執行盤後選股掃描』。")
