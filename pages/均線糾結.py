import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="台股均線糾結掃描器", layout="wide")

st.title("🏹 台股均線糾結掃描器")
st.markdown("""
### 篩選條件
- **糾結定義**：MA5, MA20, MA60 三條均線差距在 3% 以內
- **多頭確認**：股價位於季線 (MA60) 之上
- **量能確認**：今日成交量 > 5日均量
""")

# 參數設定
threshold = st.slider("糾結閾值 (均線差距 %)", 0.5, 5.0, 3.0) / 100

@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

stock_list = get_stock_list()
ticker_map = {s["ticker"]: {"code": s["code"], "name": s["name"]} for s in stock_list}
tickers = list(ticker_map.keys())

if st.button("🚀 開始糾結掃描"):
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
                    
                    close = df["Close"]
                    vol = df["Volume"]
                    
                    ma5, ma20, ma60 = close.rolling(5).mean().iloc[-1], close.rolling(20).mean().iloc[-1], close.rolling(60).mean().iloc[-1]
                    
                    # 判斷糾結：最高與最低均線差距
                    ma_vals = [ma5, ma20, ma60]
                    diff = (max(ma_vals) - min(ma_vals)) / min(ma_vals)
                    
                    # 篩選條件：糾結度、股價站上季線、成交量大於5日均量
                    if diff < threshold and close.iloc[-1] > ma60 and vol.iloc[-1] > vol.rolling(5).mean().iloc[-1]:
                        info = ticker_map[ticker]
                        results.append({
                            "代號": info["code"], "名稱": info["name"], "收盤價": round(float(close.iloc[-1]), 2),
                            "MA5": round(ma5, 2), "MA20": round(ma20, 2), "MA60": round(ma60, 2), "糾結度(%)": round(diff*100, 2)
                        })
                except: continue
        except: continue
        progress.progress((batch_idx + 1) / total_batches)

    if results:
        res_df = pd.DataFrame(results).sort_values("糾結度(%)")
        st.success(f"找到 {len(res_df)} 檔潛在糾結標的")
        st.dataframe(res_df, use_container_width=True)
    else:
        st.warning("⚠️ 未找到符合條件的標的，請嘗試調大糾結閾值。")
