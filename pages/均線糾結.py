import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="台股精準糾結掃描器", layout="wide")
st.title("🏹 台股精準糾結掃描器")

# --- 參數設定 ---
mode = st.radio("選擇糾結模式", ["3線 (5, 10, 20)", "4線 (5, 10, 20, 60)"])
threshold = st.slider("糾結閾值 (均線差距 %)", 0.5, 5.0, 2.0) / 100
min_volume = st.number_input("最小日成交量 (張)", value=500)

ma_map = {"3線 (5, 10, 20)": [5, 10, 20], "4線 (5, 10, 20, 60)": [5, 10, 20, 60]}
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

if st.button("🚀 開始精準掃描"):
    results = []
    progress = st.progress(0)
    batch_size = 150 # 降低批次量以維持穩定性
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        batch_tickers = tickers[batch_idx * batch_size : (batch_idx + 1) * batch_size]
        try:
            # 獲取資料
            data = yf.download(batch_tickers, period="6mo", interval="1d", group_by="ticker", progress=False)
            
            for ticker in batch_tickers:
                try:
                    df = data[ticker]
                    if len(df) < 80: continue # 確保有足夠歷史資料計算季線斜率
                    
                    close = df['Close']
                    vol = df['Volume']
                    
                    # 1. 計算均線與糾結度
                    ma_vals = [close.rolling(p).mean().iloc[-1] for p in periods]
                    diff = (max(ma_vals) - min(ma_vals)) / min(ma_vals)
                    
                    # 2. 濾網條件
                    ma60 = close.rolling(60).mean().iloc[-1]
                    ma60_old = close.rolling(60).mean().iloc[-11] # 10天前的季線
                    
                    is_tangled = diff < threshold
                    is_trend_up = ma60 > ma60_old # 季線斜率向上
                    is_above_ma60 = close.iloc[-1] > ma60 # 在季線之上
                    is_vol_ok = vol.iloc[-1] > vol.rolling(5).mean().iloc[-1] # 今日量大於5日均量
                    is_liquid = vol.iloc[-1] > (min_volume * 1000) # 排除殭屍股
                    
                    if is_tangled and is_trend_up and is_above_ma60 and is_vol_ok and is_liquid:
                        info = ticker_map[ticker]
                        results.append({
                            "代號": info["code"], "名稱": info["name"], 
                            "收盤價": round(float(close.iloc[-1]), 2),
                            "糾結度(%)": round(diff*100, 2)
                        })
                except: continue
        except: continue
        progress.progress((batch_idx + 1) / total_batches)

    if results:
        res_df = pd.DataFrame(results).sort_values("糾結度(%)")
        st.success(f"🔥 精準篩選出 {len(res_df)} 檔潛力標的")
        st.dataframe(res_df, use_container_width=True)
    else:
        st.warning("⚠️ 沒有符合所有條件的股票，建議調寬糾結閾值或降低成交量門檻。")
