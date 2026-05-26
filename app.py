import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

from universe import build_universe


st.set_page_config(page_title="法人 Top10 系統", layout="wide")

st.title("🏛️ 動態流動性 + 法人 Top10 系統")


# =========================
# 📈 取得資料
# =========================
def get_data(stock):

    try:
        df = yf.download(stock, period="6mo", progress=False)

        if df is None or df.empty:
            return None

        return df

    except:
        return None


# =========================
# 🧠 法人打分模型
# =========================
def score(df):

    try:
        df = df.copy()

        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()

        df = df.dropna()

        if len(df) < 60:
            return None

        momentum = df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1

        trend = (df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1]

        volatility = df["Close"].pct_change().std()

        volume = df["Volume"].mean()

        return (
            momentum * 0.4 +
            trend * 0.3 +
            np.log(volume + 1) * 0.2 +
            volatility * 0.1
        )

    except:
        return None


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 產生 Top 10 訊號"):

    # 🧠 動態股票池（重點）
    stocks = build_universe(top_n=300)

    st.write(f"📦 動態股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        df = get_data(s)

        if df is None:
            continue

        s_score = score(df)

        if s_score is None:
            continue

        results.append({
            "股票": s,
            "Score": s_score
        })

        progress.progress((i + 1) / len(stocks))

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有資料（請檢查 yfinance）")
        st.stop()

    df = df.sort_values("Score", ascending=False)

    top10 = df.head(10)

    st.subheader("🔥 Top 10 強勢股票")

    st.dataframe(top10)

    st.bar_chart(top10.set_index("股票")["Score"])
