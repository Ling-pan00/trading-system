import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock

st.set_page_config(page_title="完整監控系統", layout="wide")
st.title("📊 三池交易監控系統 (完整版)")

# --- 初始化狀態 ---
if "stock_results" not in st.session_state:
    st.session_state["stock_results"] = None
if "live_monitor" not in st.session_state:
    st.session_state["live_monitor"] = None

# --- 1. 選股掃描 ---
if st.button("🚀 執行盤後選股"):
    with st.spinner("正在掃描..."):
        # 為了測試穩定性，僅取前 20 檔
        tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:20]
        data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
        
        results = []
        for t in tickers:
            try:
                df = data[t] if len(tickers) > 1 else data
                c = df["Close"].iloc[-1]
                m5 = df["Close"].rolling(5).mean().iloc[-1]
                s = 5 if c > m5 else 2 # 簡易評分
                pool = "🚀 突破股" if s >= 5 else "🧊 回檔股"
                results.append({"代號": t, "分數": s, "池別": pool})
            except: continue
        st.session_state["stock_results"] = pd.DataFrame(results)
        st.rerun()

# --- 2. 顯示介面 ---
if st.session_state["stock_results"] is not None:
    df_all = st.session_state["stock_results"]
    
    # 三池分欄
    cols = st.columns(3)
    for i, pool in enumerate(["🚀 突破股", "🟡 動能股", "🧊 回檔股"]):
        with cols[i]:
            st.subheader(pool)
            st.dataframe(df_all[df_all["池別"] == pool], use_container_width=True)

    st.write("---")
    
    # 3. 盤中監控區塊
    st.subheader("📈 盤中即時監控")
    if st.button("🔄 更新盤中訊號"):
        live = []
        tickers = df_all["代號"].tolist()
        data = yf.download(tickers, period="2d", group_by="ticker", progress=False)
        for t in tickers:
            try:
                d = data[t] if len(tickers) > 1 else data
                sig = "🟢 強勢" if d["Close"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 觀望"
                live.append({"代號": t, "訊號": sig})
            except: continue
        st.session_state["live_monitor"] = pd.DataFrame(live)
    
    if st.session_state["live_monitor"] is not None:
        st.dataframe(st.session_state["live_monitor"], use_container_width=True)
    else:
        st.info("請點擊上方的『更新盤中訊號』按鈕以開始監控。")

    # 4. 轉折圖區塊
    st.write("---")
    st.subheader("🎯 智慧轉折圖")
    sel = st.selectbox("請選擇股票：", df_all["代號"].unique())
    if sel:
        df_k = yf.download(sel, period="6mo", progress=False)
        if not df_k.empty:
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', style='charles', returnfig=True)
            st.pyplot(fig)
        else:
            st.error("無法取得該股票 K 線數據")
else:
    st.warning("請先點擊上方按鈕執行選股。")
