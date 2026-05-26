import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

st.set_page_config(page_title="法人多因子選股系統", layout="wide")

st.title("🏛️ 法人多因子選股系統")


# =========================
# 📊 股票池（穩定 + 排ETF）
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i["Code"]

        # ✔ 只保留純股票（排 ETF / 特殊）
        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        stocks.append(code + ".TW")

    return stocks[:80]


# =========================
# 📈 多因子模型
# =========================
def alpha_score(df):

    try:
        df = df.copy()

        df["ret"] = df["Close"].pct_change()
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()

        df = df.dropna()

        if len(df) < 60:
            return 0

        momentum = df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1

        trend = (df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1]

        volatility = df["ret"].std()

        volume = df["Volume"].mean() / 1_000_000

        strength = df["Close"].iloc[-1] / df["Close"].min()

        score = (
            momentum * 0.35 +
            trend * 0.25 +
            volatility * 0.10 +
            volume * 0.15 +
            strength * 0.15
        )

        return float(score)

    except:
        return 0


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 開始法人掃描"):

    stocks = get_universe()

    st.write(f"📦 股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            if df is None or df.empty:
                continue

            score = alpha_score(df)

            results.append({
                "股票": s,
                "Alpha": score
            })

        except:
            continue

        progress.progress((i + 1) / len(stocks))

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有資料")
        st.stop()

    df = df.sort_values("Alpha", ascending=False)

    st.subheader("📊 法人多因子排名")

    st.dataframe(df.head(20))

    st.bar_chart(df.set_index("股票")["Alpha"])
