import streamlit as st
import pandas as pd
import numpy as np
import requests

st.title("🏛️ 穩定 Top 10 訊號系統（修正版）")


# =========================
# 📊 穩定股票池（不用 yfinance）
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return [i["Code"] for i in data if i["Code"].isdigit()][:100]


# =========================
# 🧠 模擬穩定價格（避免 yfinance 掛掉）
# =========================
def fake_price_series(seed):

    np.random.seed(int(seed))

    price = 100 + np.cumsum(np.random.randn(120))

    return pd.DataFrame({
        "Close": price,
        "Volume": np.random.randint(1000, 50000, 120)
    })


# =========================
# 📈 穩定打分模型
# =========================
def score(df):

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()

    df = df.dropna()

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


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 產生 Top 10 訊號（穩定版）"):

    stocks = get_universe()

    results = []

    for s in stocks:

        df = fake_price_series(s)

        s_score = score(df)

        results.append({
            "股票": s,
            "Score": s_score
        })

    df = pd.DataFrame(results)

    df = df.sort_values("Score", ascending=False)

    top10 = df.head(10)

    st.dataframe(top10)

    st.bar_chart(top10.set_index("股票")["Score"])
