import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

st.title("🏛️ 法人級 Top 10 選股系統（真實版）")


# =========================
# 📊 股票池（已排 ETF）
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i["Code"]

        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        # 🚨 ETF / ETN 排除
        if code.startswith(("00", "006", "008", "009")):
            continue

        stocks.append(code + ".TW")

    return stocks[:100]


# =========================
# 📈 真實資料
# =========================
def get_price(stock):

    df = yf.download(stock, period="6mo", progress=False)

    if df is None or df.empty:
        return None

    return df


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
if st.button("🚀 產生 Top 10（真實法人版）"):

    stocks = get_universe()

    st.write(f"📦 股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        df = get_price(s)

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
        st.warning("沒有資料（yfinance 抓不到）")
        st.stop()

    df = df.sort_values("Score", ascending=False)

    top10 = df.head(10)

    st.subheader("🔥 Top 10 強勢股票")

    st.dataframe(top10)

    st.bar_chart(top10.set_index("股票")["Score"])
