import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="穩定選股系統", layout="wide")

st.title("🏛️ 穩定正式選股系統（Professional Stable Edition）")

# =========================
# 📌 股票池（穩定版：200檔內）
# =========================
stocks = [
    "2330.TW","2317.TW","2454.TW","2382.TW","2303.TW",
    "2308.TW","2412.TW","2881.TW","2882.TW","2891.TW",
    "2886.TW","2603.TW","2615.TW","2002.TW","1101.TW",
    "1301.TW","1303.TW","1326.TW","2207.TW","2357.TW"
]

top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 🧠 安全轉換
# =========================
def safe(x):
    try:
        return float(np.array(x).item())
    except:
        return np.nan


# =========================
# 📊 技術計分（穩定核心）
# =========================
def score(df):

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

    # 📉 跌深反彈
    if -20 < bias < -8:
        score += 30

    # 📊 量能
    if vol > vol_ma:
        score += 20

    # 📈 趨勢
    if close > df["Close"].rolling(60).mean().iloc[i]:
        score += 20

    # 🚀 突破
    if close > df["High"].rolling(20).max().iloc[i-1]:
        score += 30

    return {
        "score": score,
        "bias": bias,
        "price": close
    }


# =========================
# 🚀 安全下載（防 crash）
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
# 🚀 主程式
# =========================
if st.button("🚀 開始掃描（穩定版）"):

    results = []
    progress = st.progress(0)

    for idx, s in enumerate(stocks):

        df = get_data(s)

        r = score(df)

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
        st.warning("今天沒有符合條件的股票")
    else:

        df_result = df_result.sort_values("分數", ascending=False)

        st.subheader("🏆 Top 選股結果")
        st.dataframe(df_result.head(top_n))

        st.subheader("📊 分數分布")
        st.bar_chart(df_result.set_index("股票")["分數"])
