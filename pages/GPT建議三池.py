import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock

# 設定頁面資訊
st.set_page_config(page_title="三池交易監控系統", layout="wide")
st.title("📊 三池交易監控系統 (完整穩定模組版)")

# --- 統一資料清理模組 ---
def clean_df(df):
    """確保資料格式標準化，防止 KeyError"""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # 確保必要欄位存在
    required = ['Open', 'High', 'Low', 'Close']
    if all(col in df.columns for col in required):
        return df.dropna(subset=required)
    return None

# --- 1. 選股掃描模組 ---
if "stock_results" not in st.session_state: 
    st.session_state["stock_results"] = None

if st.button("🚀 執行完整盤後選股"):
    with st.spinner("掃描中..."):
        # 抓取清單 (確保僅讀取 4 碼上市公司)
        tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:100]
        res = []
        for t in tickers:
            try:
                # 單檔下載，避免批量結構錯亂
                raw_df = yf.download(t, period="3mo", progress=False)
                df = clean_df(raw_df)
                if df is not None and len(df) > 20:
                    c, m5 = df["Close"].iloc[-1], df["Close"].rolling(5).mean().iloc[-1]
                    s = 5 if c > m5 else 2
                    pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
                    res.append({"代號": t.replace(".TW", ""), "分數": s, "池別": pool})
            except: continue
        st.session_state["stock_results"] = pd.DataFrame(res)
        st.rerun()

# --- 2. 顯示與互動模組 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    
    # 顯示分類表格
    cols = st.columns(3)
    for i, p in enumerate(["🚀 突破股", "🟡 動能股", "🧊 回檔股"]):
        with cols[i]:
            st.subheader(p)
            st.dataframe(df_res[df_res["池別"] == p], use_container_width=True, hide_index=True)

    # --- 轉折 K 線圖 (獨立區塊) ---
    st.write("---")
    st.subheader("🎯 轉折 K 線圖")
    sel = st.selectbox("選擇股票：", df_res["代號"].unique())
    if sel:
        raw_df = yf.download(f"{sel}.TW", period="6mo", progress=False)
        df_k = clean_df(raw_df)
        if df_k is not None:
            ma5 = df_k['Close'].rolling(5).mean()
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=mpf.make_addplot(ma5, color='orange'), 
                               style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
        else:
            st.error("無法取得該檔股票 K 線資料")

    # --- 盤中監控 (獨立區塊) ---
    st.write("---")
    st.subheader("📈 盤中監控")
    if st.button("🔄 更新盤中訊號"):
        live_res = []
        for t in df_res["代號"].unique():
            try:
                df = clean_df(yf.download(f"{t}.TW", period="2d", progress=False))
                if df is not None:
                    sig = "🟢 強勢" if df["Close"].iloc[-1] >= df["Close"].iloc[-2] else "🟡 觀望"
                    live_res.append({"代號": t, "訊號": sig})
            except: continue
        st.dataframe(pd.DataFrame(live_res), use_container_width=True)
else:
    st.info("💡 請點擊上方按鈕執行掃描以開始使用。")
