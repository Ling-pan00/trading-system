import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import twstock

# 頁面配置
st.set_page_config(page_title="三池交易監控系統", layout="wide")
st.title("📊 三池交易監控系統 (最終穩定版)")

# --- 安全資料獲取 ---
@st.cache_data(ttl=3600)
def fetch_safe_data(ticker, period="3mo"):
    try:
        df = yf.download(ticker, period=period, progress=False)
        # 處理 MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # 檢查欄位完整性
        required = ['Open', 'High', 'Low', 'Close']
        if not all(col in df.columns for col in required):
            return None
        return df.dropna()
    except:
        return None

# --- 選股邏輯 ---
if "stock_results" not in st.session_state: st.session_state["stock_results"] = None

if st.button("🚀 執行盤後選股掃描"):
    with st.spinner("正在逐檔掃描市場，請稍候..."):
        all_tickers = [f"{c}.TW" for c, i in twstock.codes.items() if i.market == "上市" and len(c) == 4][:100]
        res = []
        for t in all_tickers:
            df = fetch_safe_data(t, "3mo")
            if df is not None and len(df) > 20:
                c, m5 = df["Close"].iloc[-1], df["Close"].rolling(5).mean().iloc[-1]
                s = 5 if c > m5 else 2
                pool = "🚀 突破股" if s >= 5 else "🟡 動能股" if s >= 3 else "🧊 回檔股"
                res.append({"代號": t.replace(".TW", ""), "ticker": t, "分數": s, "池別": pool})
        
        df_res = pd.DataFrame(res)
        st.session_state["stock_results"] = df_res.groupby("池別").apply(lambda x: x.nlargest(10, '分數')).reset_index(drop=True)
        st.rerun()

# --- 介面顯示 ---
if st.session_state["stock_results"] is not None:
    df_res = st.session_state["stock_results"]
    cols = st.columns(3)
    for i, p in enumerate(["🚀 突破股", "🟡 動能股", "🧊 回檔股"]):
        with cols[i]:
            st.subheader(p)
            st.dataframe(df_res[df_res["池別"] == p][["代號", "分數"]], use_container_width=True, hide_index=True)

    # 轉折 K 線圖
    st.write("---")
    st.subheader("🎯 轉折 K 線圖")
    sel = st.selectbox("請選擇股票進行分析：", df_res["ticker"].unique())
    
    if sel:
        df_k = fetch_safe_data(sel, "6mo")
        if df_k is not None:
            ma5 = df_k['Close'].rolling(5).mean()
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', addplot=mpf.make_addplot(ma5, color='orange'), 
                               style='charles', volume=True, returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
        else:
            st.error("該股票目前無有效交易數據。")
else:
    st.info("💡 請點擊『執行盤後選股掃描』以載入資料。")
