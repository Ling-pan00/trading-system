import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock

# 頁面配置
st.set_page_config(page_title="三池交易監控系統", layout="wide")
st.title("📊 三池交易監控系統 Pro (最終穩定版)")

# --- 核心邏輯：資料預處理 ---
def clean_data(df):
    """強制修正 yfinance 回傳的多層結構與空值"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(subset=['Open', 'High', 'Low', 'Close'])

# --- 1. 選股與分池 ---
if "stock_results" not in st.session_state: st.session_state["stock_results"] = None

if st.button("🚀 執行完整盤後選股"):
    with st.spinner("正在進行市場掃描與分池..."):
        # 抓取台股標的
        tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:150]
        data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
        
        results = []
        for t in tickers:
            try:
                df = data[t] if len(tickers) > 1 else data
                df = clean_data(df)
                if len(df) < 20: continue
                
                c, m5 = df["Close"].iloc[-1], df["Close"].rolling(5).mean().iloc[-1]
                s = 5 if c > m5 else 2
                pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
                results.append({"代號": t.replace(".TW", ""), "ticker": t, "分數": s, "池別": pool})
            except: continue
        
        # 強制分組取前 10
        df_res = pd.DataFrame(results)
        st.session_state["stock_results"] = df_res.groupby("池別").apply(lambda x: x.nlargest(10, '分數')).reset_index(drop=True)
        st.rerun()

# --- 2. 顯示介面 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    cols = st.columns(3)
    for i, p in enumerate(["🚀 突破股", "🟡 動能股", "🧊 回檔股"]):
        with cols[i]:
            st.subheader(p)
            target = df_res[df_res["池別"] == p]
            st.dataframe(target[["代號", "分數"]], use_container_width=True, hide_index=True)

    # 3. 盤中監控
    st.write("---")
    st.subheader("📈 盤中即時訊號")
    if st.button("🔄 更新監控訊號"):
        live = []
        active = df_res["ticker"].unique().tolist()
        data = yf.download(active, period="2d", group_by="ticker", progress=False)
        for t in active:
            try:
                d = clean_data(data[t] if len(active) > 1 else data)
                sig = "🟢 強勢" if d["Close"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 觀望"
                live.append({"代號": t.replace(".TW", ""), "訊號": sig})
            except: continue
        st.session_state["live_monitor"] = pd.DataFrame(live)
    
    if "live_monitor" in st.session_state:
        st.dataframe(st.session_state["live_monitor"], use_container_width=True)

    # 4. 轉折圖 (關鍵修復：防止 ValueError)
    st.write("---")
    st.subheader("🎯 轉折 K 線圖")
    sel = st.selectbox("選擇股票進行分析：", df_res["ticker"].unique())
    if sel:
        df_k = clean_data(yf.download(sel, period="6mo", progress=False))
        if not df_k.empty:
            ma5 = df_k['Close'].rolling(5).mean()
            ap = [mpf.make_addplot(ma5, color='orange')]
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=ap, style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
        else:
            st.error("此股票目前無有效交易數據。")
else:
    st.info("💡 請點擊『執行完整盤後選股』開始分析。")
