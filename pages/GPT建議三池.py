import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock

st.set_page_config(page_title="三池交易監控系統", layout="wide")
st.title("📊 三池交易監控系統 (究極防錯版)")

# --- 安全存取資料 ---
def get_safe_df(df):
    """確保資料結構為單層索引，且包含必要欄位"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    if all(col in df.columns for col in required):
        return df.dropna()
    return None

# --- 選股邏輯 ---
if "stock_results" not in st.session_state: st.session_state["stock_results"] = None

if st.button("🚀 執行盤後選股掃描"):
    with st.spinner("正在安全掃描市場..."):
        tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:100]
        res = []
        for t in tickers:
            try:
                raw_df = yf.download(t, period="3mo", progress=False)
                df = get_safe_df(raw_df)
                if df is not None and len(df) > 20:
                    c, m5 = df["Close"].iloc[-1], df["Close"].rolling(5).mean().iloc[-1]
                    s = 5 if c > m5 else 2
                    pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
                    res.append({"代號": t.replace(".TW", ""), "ticker": t, "分數": s, "池別": pool})
            except: continue
        
        df_res = pd.DataFrame(res)
        st.session_state["stock_results"] = df_res.groupby("池別").apply(lambda x: x.nlargest(10, '分數')).reset_index(drop=True)
        st.rerun()

# --- 介面 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    cols = st.columns(3)
    for i, p in enumerate(["🚀 突破股", "🟡 動能股", "🧊 回檔股"]):
        with cols[i]:
            st.subheader(p)
            st.dataframe(df_res[df_res["池別"] == p][["代號", "分數"]], use_container_width=True, hide_index=True)

    st.write("---")
    st.subheader("🎯 轉折 K 線圖")
    sel = st.selectbox("選擇股票：", df_res["ticker"].unique())
    if sel:
        raw_df = yf.download(sel, period="6mo", progress=False)
        df_k = get_safe_df(raw_df)
        if df_k is not None:
            ma5 = df_k['Close'].rolling(5).mean()
            ap = [mpf.make_addplot(ma5, color='orange')]
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=ap, style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
        else:
            st.error("無法繪圖：資料格式異常或資料缺失。")
