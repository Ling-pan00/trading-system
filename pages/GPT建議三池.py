import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock

st.set_page_config(page_title="三池完整監控系統", layout="wide")
st.title("📊 三池交易監控系統 (穩定修正版)")

# --- 1. 選股與分池邏輯 ---
if "stock_results" not in st.session_state: st.session_state["stock_results"] = None
if "live_monitor" not in st.session_state: st.session_state["live_monitor"] = None

if st.button("🚀 執行盤後選股"):
    with st.spinner("正在掃描並進行分池排序..."):
        # 取得台股清單並取樣
        tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:150]
        data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
        
        results = []
        for t in tickers:
            try:
                df = data[t] if len(tickers) > 1 else data
                c = df["Close"].iloc[-1]
                m5, m10, m20 = df["Close"].rolling(5).mean().iloc[-1], df["Close"].rolling(10).mean().iloc[-1], df["Close"].rolling(20).mean().iloc[-1]
                # 評分邏輯
                s = (2 if c > m5 else 0) + (1 if m5 > m10 else 0) + (1 if m10 > m20 else 0)
                pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
                results.append({"代號": t.replace(".TW", ""), "分數": s, "池別": pool})
            except: continue
        
        # 強制執行分池與數量平衡 (每池取前 5 檔)
        df_all = pd.DataFrame(results)
        st.session_state["stock_results"] = (
            df_all.sort_values(["池別", "分數"], ascending=[True, False])
            .groupby("池別")
            .head(5)
        )
        st.rerun()

# --- 2. 介面顯示 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    
    # 三欄並排顯示
    cols = st.columns(3)
    pools = ["🚀 突破股", "🟡 動能股", "🧊 回檔股"]
    for i, pool in enumerate(pools):
        with cols[i]:
            st.subheader(pool)
            st.dataframe(df_res[df_res["池別"] == pool], use_container_width=True, hide_index=True)

    st.write("---")
    
    # 3. 盤中監控 (持久化)
    st.subheader("📈 盤中即時監控")
    if st.button("🔄 更新盤中訊號"):
        live = []
        tickers = [f"{t}.TW" for t in df_res["代號"]]
        data = yf.download(tickers, period="2d", group_by="ticker", progress=False)
        for t in tickers:
            try:
                d = data[t] if len(tickers) > 1 else data
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                sig = "🟢 強勢" if d["Close"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 觀望"
                live.append({"代號": t.replace(".TW", ""), "訊號": sig})
            except: continue
        st.session_state["live_monitor"] = pd.DataFrame(live)
    
    if st.session_state["live_monitor"] is not None:
        st.dataframe(st.session_state["live_monitor"], use_container_width=True, hide_index=True)

    # 4. 轉折圖 (資料防錯)
    st.write("---")
    st.subheader("🎯 智慧轉折 K 線圖")
    sel_code = st.selectbox("選擇股票：", df_res["代號"].unique())
    if sel_code:
        df_k = yf.download(f"{sel_code}.TW", period="6mo", progress=False)
        if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
        
        if not df_k.empty:
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
else:
    st.info("💡 請先點擊上方『執行盤後選股』以載入資料。")
