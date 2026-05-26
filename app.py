import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

st.set_page_config(page_title="法人打分選股系統", layout="wide")

st.title("🏛️ 法人多因子打分選股系統 v2")


# =========================
# 📊 股票池
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:
        code = i["Code"]

        if code.isdigit():
            stocks.append(code + ".TW")

    return stocks[:60]


# =========================
# 📈 打分模型（核心）
# =========================
def score_stock(df):

    try:
        df = df.copy()

        df["ret"] = df["Close"].pct_change()
        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()

        df = df.dropna()

        if len(df) < 60:
            return 0

        # =========================
        # 🟢 1. 流動性分數
        # =========================
        liquidity = np.log(df["Volume"].mean() + 1)

        # =========================
        # 🟡 2. 動能分數
        # =========================
        momentum = df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1

        # =========================
        # 🟡 3. 趨勢分數
        # =========================
        trend = (df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1]

        # =========================
        # 🔵 4. 波動分數（適中最好）
        # =========================
        volatility = df["ret"].std()

        # =========================
        # 🧠 加權 Alpha Score
        # =========================
        score = (
            liquidity * 0.25 +
            momentum * 0.35 +
            trend * 0.25 +
            volatility * 0.15
        )

        return float(score)

    except:
        return 0


# =========================
# 📊 主程式
# =========================
if st.button("🚀 開始法人打分掃描"):

    stocks = get_universe()

    st.write(f"📦 股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            if df is None or df.empty:
                continue

            score = score_stock(df)

            results.append({
                "股票": s,
                "Alpha Score": score
            })

        except:
            continue

        progress.progress((i + 1) / len(stocks))

    result_df = pd.DataFrame(results)

    if result_df.empty:
        st.warning("沒有資料（請檢查資料源）")
        st.stop()

    result_df = result_df.sort_values("Alpha Score", ascending=False)

    st.subheader("📊 法人 Alpha 排名 Top 20")

    st.dataframe(result_df.head(20))

    st.bar_chart(result_df.head(20).set_index("股票")["Alpha Score"])
