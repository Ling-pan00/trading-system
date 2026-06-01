import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock
import numpy as np

# 設定頁面
st.set_page_config(page_title="三池完整監控系統", layout="wide")
st.title("📊 三池交易監控系統 (系統穩定版)")

# --- 1. 股票池與資料下載 ---
@st.cache_data(ttl=3600)
def get_data():
    tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:150]
    data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
    return data, tickers

if "stock_results" not in st.session_state: st.session_state["stock_results"] = None
if "live_monitor" not in st.session_state: st.session_state["live_monitor"] = None

# --- 2. 核心選股掃描 ---
if st.button("🚀 執行完整盤後選股"):
    with st.spinner("正在進行市場分析..."):
        data, tickers = get_data()
        results = []
        for t in tickers:
            try:
                df = data[t] if len(tickers) > 1 else data
                if df.empty or len(df) < 20: continue
                c = df["Close"].iloc[-1]
                m5 = df["Close"].rolling(5).mean().iloc[-1]
                # 分數邏輯 (調整為更寬鬆的區間，確保不會空)
                s = 5 if c > m5 else 2
                pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
                results.append({"代號": t.replace(".TW", ""), "分數": s, "池別": pool})
            except: continue
        
        # 強制平衡每一池，如果某一池不足，至少顯示該池所有結果
        df_res = pd.DataFrame(results)
        st.session_state["stock_results"] = (
            df_res.sort_values(["池別", "分數"], ascending=[True, False])
            .groupby("池別")
            .head(10)
        )
        st.rerun()

# --- 3. UI 介面與顯示 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    
    # 三池展示
    cols = st.columns(3)
    pools = ["🚀 突破股", "🟡 動能股", "🧊 回檔股"]
    for i, pool in enumerate(pools):
        with cols[i]:
            st.subheader(pool)
            target = df_res[df_res["池別"] == pool]
            st.dataframe(target if not target.empty else pd.DataFrame([{"訊息": "無股票入選"}]), 
                         use_container_width=True, hide_index=True)

    st.write("---")
    
    # 盤中監控
    st.subheader("📈 盤中即時監控")
    if st.button("🔄 更新監控狀態"):
        live = []
        # 從選股結果中抓取 ticker
        active_tickers = [f"{t}.TW" for t in df_res["代號"].unique()]
        live_data = yf.download(active_tickers, period="2d", group_by="ticker", progress=False)
        
        for t in active_tickers:
            try:
                d = live_data[t] if len(active_tickers) > 1 else live_data
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                sig = "🟢 強勢" if d["Close"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 觀望"
                live.append({"代號": t.replace(".TW", ""), "訊號": sig})
            except: continue
        st.session_state["live_monitor"] = pd.DataFrame(live)
    
    if st.session_state["live_monitor"] is not None:
        st.dataframe(st.session_state["live_monitor"], use_container_width=True, hide_index=True)

    # 轉折圖
    st.write("---")
    st.subheader("🎯 智慧轉折 K 線圖")
    sel = st.selectbox("選擇股票分析：", df_res["代號"].unique())
    if sel:
        df_k = yf.download(f"{sel}.TW", period="6mo", progress=False)
        if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
        if not df_k.empty:
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
else:
    st.info("請點擊『執行完整盤後選股』開始分析。")
