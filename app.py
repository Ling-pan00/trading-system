import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
st.set_page_config(page_title="雙模式選股系統", layout="wide")
st.title("🏛️ 雙模式選股系統（Professional Dual Mode）")
# =========================
# 📌 股票池（穩定版）
# =========================
stocks = [
    "2330.TW","2317.TW","2454.TW","2382.TW","2303.TW",
    "2308.TW","2412.TW","2881.TW","2882.TW","2891.TW",
    "2886.TW","2603.TW","2615.TW","2002.TW","1101.TW",
    "1301.TW","1303.TW","1326.TW","2207.TW","2357.TW"
]
mode = st.radio("選擇模式", ["🟢 嚴格模式（高勝率）", "🟡 寬鬆模式（高訊號）"])
top_n = st.slider("顯示前幾名", 5, 20, 10)
# =========================
# 🧠 安全數值
# =========================
def safe(x):
    try:
        return float(np.array(x).item())
    except:
        return np.nan
# =========================
# 📊 計分模型（雙模式核心）
# =========================
def score(df, mode):
    if df is None or df.empty or len(df) < 120:
        return None
    i = len(df) - 1
    close = safe(df["Close"].iloc[i])
    ma20 = safe(df["Close"].rolling(20).mean().iloc[i])
    vol = safe(df["Volume"].iloc[i])
    vol_ma = safe(df["Volume"].rolling(5).mean().iloc[i])
    if np.isnan(close) or np.isnan(ma20) or ma20 == 0:
        return None
    bias = ((close - ma20) / ma20) * 100
    score = 0
    # =========================
    # 🟢 嚴格模式（高勝率）
    # =========================
    if mode == "🟢 嚴格模式（高勝率）":
        if -20 < bias < -8:
            score += 35
        if vol > vol_ma:
            score += 25
        if close > df["Close"].rolling(60).mean().iloc[i]:
            score += 20
        if close > df["High"].rolling(20).max().iloc[i-1]:
            score += 20
    # =========================
    # 🟡 寬鬆模式（高訊號）
    # =========================
    else:
        if -30 < bias < 5:
            score += 25
        if vol > vol_ma:
            score += 20
        if close > df["Close"].rolling(60).mean().iloc[i]:
            score += 20
        # 放寬突破條件（重要）
        if close > df["Close"].rolling(20).mean().iloc[i]:
            score += 15
    return {
        "score": score,
        "bias": bias,
        "price": close
    }
# =========================
# 🚀 下載
# =========================
def get_data(symbol):
    try:
        df = yf.download(symbol, period="6mo", progress=False, threads=True)
        if df is None or df.empty or len(df) < 120:
            return None
        return df
    except:
        return None
# =========================
# 🚀 掃描
# =========================
if st.button("🚀 開始掃描"):
    results = []
    progress = st.progress(0)
    for idx, s in enumerate(stocks):
        df = get_data(s)
        r = score(df, mode)
        if r:
            results.append({
                "股票": s,
                "分數": r["score"],
                "乖離%": round(r["bias"], 2),
                "收盤價": round(r["price"], 2)
            })
        progress.progress((idx + 1) / len(stocks))
    df_result = pd.DataFrame(results)
    if df_result.empty:
        st.warning("今天沒有符合條件的股票（可切換寬鬆模式）")
    else:
        df_result = df_result.sort_values("分數", ascending=False)
        st.subheader("🏆 選股結果")
        st.dataframe(df_result.head(top_n))
        st.subheader("📊 分數分布")
        st.bar_chart(df_result.set_index("股票")["分數"])
