import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="台股均線糾結掃描器", layout="wide")

st.title("🎯 台股均線糾結掃描器 (自訂版)")

# 參數設定
mode = st.radio("選擇糾結模式", ["3線 (5, 10, 20)", "4線 (5, 10, 20, 60)"])
threshold = st.slider("糾結閾值 (均線差距 %)", 0.5, 5.0, 2.0) / 100

# 定義週期對應
ma_map = {
    "3線 (5, 10, 20)": [5, 10, 20],
    "4線 (5, 10, 20, 60)": [5, 10, 20, 60]
}
periods = ma_map[mode]

@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

tickers = [s["ticker"] for s in get_stock_list()]
ticker_map = {s["ticker"]: {"code": s["code"], "name": s["name"]} for s in get_stock_list()}

if st.button("🚀 開始掃描"):
    results = []
    progress = st.progress(0)
    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        batch_tickers = tickers[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        try:
            data = yf.download(batch_tickers, period="6mo", interval="1d", group_by="ticker", progress=False)
            for ticker in batch_tickers:
                try:
                    df = data[ticker]
                    if len(df) < 65: continue
                    
                    # 動態計算各週期均線
                    ma_vals = [df['Close'].rolling(p).mean().iloc[-1] for p in periods]
                    diff = (max(ma_vals) - min(ma_vals)) / min(ma_vals)
                    
                    # 篩選：糾結度小於閾值 且 今日收盤 > 5日均線 (表開始有買盤)
                    if diff < threshold and df['Close'].iloc[-1] > df['Close'].rolling(5).mean().iloc[-1]:
                        info = ticker_map[ticker]
                        results.append({
                            "代號": info["code"], "名稱": info["name"], 
                            "糾結度(%)": round(diff*100, 2),
                            **{f"MA{p}": round(ma_vals[i], 2) for i, p in enumerate(periods)}
                        })
                except: continue
        except: continue
        progress.progress((batch_idx + 1) / total_batches)

    if results:
        res_df = pd.DataFrame(results).sort_values("糾結度(%)")
        st.success(f"找到 {len(res_df)} 檔潛在糾結標的")
        st.dataframe(res_df, use_container_width=True)
    else:
        st.warning("⚠️ 未找到符合條件的標的。")
