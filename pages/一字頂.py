import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ==========================================
# ⚙️ Streamlit 頁面設定
# ==========================================
st.set_page_config(page_title="一字頂反轉策略 Pro", layout="wide")
st.title("📊 一字頂（平頂阻力）反轉量化交易系統")
st.markdown("本系統篩選股價多次觸及同一高點壓力（一字頂），且近期出現轉弱訊號的標的。")

# ==========================================
# 📦 股票池模組
# ==========================================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
                stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

st.write(f"📦 **目前監測台股總數：{len(tickers)} 檔**")

# ==========================================
# 📈 技術指標與一字頂邏輯
# ==========================================
def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    return df

def check_flat_top(df):
    """偵測一字頂：多個高點落於 1.2% 區間內"""
    try:
        if len(df) < 80: return False, 0, 0
        recent = df.iloc[-80:]
        highs = recent["High"].values
        
        # 尋找區域波段高點
        peaks = []
        for i in range(5, len(highs)-5):
            if highs[i] == max(highs[i-5:i+6]):
                peaks.append(highs[i])
        
        if len(peaks) < 2: return False, 0, 0
        
        # 檢查是否有平頂 (價格極度接近)
        peaks = sorted(peaks, reverse=True)
        top = peaks[0]
        for p in peaks[1:]:
            if abs(top - p) / top <= 0.012: # 1.2% 誤差範圍
                level = (top + p) / 2
                # 條件：現價位於平頂附近，且跌破 5MA
                if (df["Close"].iloc[-1] <= level * 1.03) and (df["Close"].iloc[-1] <= df["ma5"].iloc[-1]):
                    return True, level, df["Low"].iloc[-30:].min()
        return False, 0, 0
    except:
        return False, 0, 0

# ==========================================
# 🎨 圖表繪製與 UI 渲染
# ==========================================
def draw_chart(ticker, name):
    df = yf.download(ticker, period="6mo", progress=False)
    if df.empty: return
    
    mc = mpf.make_marketcolors(up='red', down='green', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc)
    
    fig, ax = mpf.plot(df, type='candle', style=style, volume=True, returnfig=True, figsize=(10, 5))
    st.pyplot(fig)

# ==========================================
# 🚀 主程式選股邏輯
# ==========================================
if st.button("🚀 執行一字頂策略選股"):
    results = []
    progress = st.progress(0)
    
    for idx, t in enumerate(tickers):
        try:
            df = yf.download(t, period="6mo", progress=False)
            if df.empty or (df["Volume"].iloc[-1] / 1000) < 800: continue
            
            df = add_indicators(df)
            is_flat, level, support = check_flat_top(df)
            
            if is_flat:
                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "一字頂價": round(level, 2),
                    "收盤價": round(df["Close"].iloc[-1], 2),
                    "支撐參考": round(support, 2)
                })
        except: continue
        if idx % 20 == 0: progress.progress(idx / len(tickers))
    
    progress.progress(1.0)
    st.session_state["results"] = pd.DataFrame(results)

# ==========================================
# 📊 結果顯示
# ==========================================
if "results" in st.session_state and not st.session_state["results"].empty:
    st.subheader("📊 符合一字頂策略之個股")
    st.dataframe(st.session_state["results"], use_container_width=True)
    
    # 選股瀏覽
    select_name = st.selectbox("選擇要查看的個股:", st.session_state["results"]["名稱"].tolist())
    target = st.session_state["results"][st.session_state["results"]["名稱"] == select_name].iloc[0]
    
    ticker_code = [k for k, v in ticker_map.items() if v["name"] == select_name][0]
    draw_chart(ticker_code, select_name)
else:
    st.info("請點擊上方按鈕執行掃描")
