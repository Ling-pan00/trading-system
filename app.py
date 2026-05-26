import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

from universe import build_dynamic_universe

st.set_page_config(page_title="Top 10 訊號系統", layout="wide")

st.title("🏛️ 法人 Top 10 訊號系統")


# =========================
# 📈 Alpha 打分模型
# =========================
def score(df):

    try:
        df = df.copy()

        df["ret"] = df["Close"].pct_change()
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()

        df = df.dropna()

        if len(df) < 60:
            return None

        momentum = df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1

        trend = (df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1]

        volatility = df["ret"].std()

        volume = df["Volume"].mean()

        score = (
            momentum * 0.4 +
            trend * 0.3 +
            np.log(volume + 1) * 0.2 +
            volatility * 0.1
        )

        return float(score)

    except:
        return None


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 產生 Top 10 訊號"):

    stocks = build_dynamic_universe()

    st.write(f"📦 動態股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            if df is None or df.empty:
                continue

            s_score = score(df)

            if s_score is None:
                continue

            results.append({
                "股票": s,
                "Alpha Score": s_score
            })

        except:
            continue

        progress.progress((i + 1) / len(stocks))

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有可用訊號（資料不足）")
        st.stop()

    df = df.sort_values("Alpha Score", ascending=False)

    top10 = df.head(10)

    st.subheader("🔥 Top 10 強勢訊號")

    st.dataframe(top10)

    st.bar_chart(top10.set_index("股票")["Alpha Score"])
