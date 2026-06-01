import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock
import numpy as np

# 設定頁面版面
st.set_page_config(page_title="三池完整監控系統", layout="wide")
st.title("📊 三池獨立交易監控系統 Pro ✖ 轉折波段連線")

# --- 1. 核心指標計算邏輯 ---
def calculate_score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
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

# --- 2. 選股與分池邏輯 ---
if "stock_results" not in st.session_state: st.session_state["stock_results"] = None
if "live_monitor" not in st.session_state: st.session_state["live_monitor"] = None

if st.button("🚀 執行完整盤後選股"):
    with st.spinner("正在進行深度市場評分..."):
        # 抓取台股清單
        tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:200]
        data = yf.download(tickers, period="3mo", group_by="ticker", progress=False)
        
        results = []
        for t in tickers:
            try:
                df = data[t] if len(tickers) > 1 else data
                if df.empty or len(df) < 20: continue
                close, vol = df["Close"], df["Volume"]
                ma5, ma10, ma20 = close.rolling(5).mean().iloc[-1], close.rolling(10).mean().iloc[-1], close.rolling(20).mean().iloc[-1]
                vol_ma5 = vol.rolling(5).mean().iloc[-1]
                pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
                
                s = calculate_score(close.iloc[-1], ma5, ma10, ma20, vol.iloc[-1], vol_ma5, pct)
                results.append({"代號": t.replace(".TW", ""), "ticker": t, "分數": s, "池別": classify_pool(s)})
            except: continue
        
        # 強制分池並確保每一池都有資料
        df_res = pd.DataFrame(results)
        final_list = []
        for p in ["🚀 突破股", "🟡 動能股", "🧊 回檔股"]:
            subset = df_res[df_res["池別"] == p].sort_values("分數", ascending=False)
            final_list.append(subset.head(10))
        st.session_state["stock_results"] = pd.concat(final_list)
        st.rerun()

# --- 3. 介面與顯示 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    cols = st.columns(3)
    for i, p in enumerate(["🚀 突破股", "🟡 動能股", "🧊 回檔股"]):
        with cols[i]:
            st.subheader(p)
            st.dataframe(df_res[df_res["池別"] == p][["代號", "分數"]], use_container_width=True, hide_index=True)

    st.write("---")
    
    # 4. 盤中監控
    st.subheader("📈 盤中監控")
    if st.button("🔄 更新訊號"):
        live = []
        active = df_res["ticker"].unique().tolist()
        data = yf.download(active, period="5d", group_by="ticker", progress=False)
        for t in active:
            try:
                d = data[t] if len(active) > 1 else data
                if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
                # 監控指標：突破昨高或強勢開盤
                sig = "🟢 BUY (強勢)" if d["Open"].iloc[-1] >= d["Close"].iloc[-2] else "🟡 WATCH"
                live.append({"代號": t.replace(".TW", ""), "訊號": sig})
            except: continue
        st.session_state["live_monitor"] = pd.DataFrame(live)
    
    if "live_monitor" in st.session_state:
        st.dataframe(st.session_state["live_monitor"], use_container_width=True)

    # 5. 轉折 K 線圖 (內含均線與格式防錯)
    st.write("---")
    st.subheader("🎯 轉折 K 線圖")
    sel = st.selectbox("選擇股票：", df_res["ticker"].unique())
    if sel:
        df_k = yf.download(sel, period="6mo", progress=False)
        if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
        
        if not df_k.empty:
            ap = [mpf.make_addplot(df_k['Close'].rolling(5).mean(), color='orange', label='5MA')]
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=ap, style='charles', 
                               volume=True, returnfig=True, figsize=(10, 6))
            st.pyplot(fig)
else:
    st.info("💡 請先點擊『執行完整盤後選股』開始分析。")     
