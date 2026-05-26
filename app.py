import streamlit as st
import pandas as pd
import numpy as np
import requests

from universe import build_universe


st.title("🏛️ 穩定法人 Top10（TWSE純資料版）")


# =========================
# 📊 直接抓 TWSE 日成交資料
# =========================
def get_twse_data(stock_code):

    try:
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params = {
            "stockNo": stock_code.replace(".TW", ""),
            "response": "json"
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        if "data" not in data:
            return None

        df = pd.DataFrame(data["data"], columns=data["fields"])

        # 收盤價整理
        df["close"] = df["收盤價"].str.replace(",", "").astype(float)

        return df

    except:
        return None


# =========================
# 🧠 穩定打分模型
# =========================
def score(df):

    try:
        df = df.copy()

        if len(df) < 20:
            return None

        df["ma5"] = df["close"].rolling(5).mean()
        df["ma20"] = df["close"].rolling(20).mean()

        df = df.dropna()

        momentum = df["close"].iloc[-1] / df["close"].iloc[-5] - 1

        trend = (df["ma5"].iloc[-1] - df["ma20"].iloc[-1]) / df["ma20"].iloc[-1]

        return momentum * 0.6 + trend * 0.4

    except:
        return None


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 產生 Top10（穩定版）"):

    stocks = build_universe(top_n=200)

    st.write(f"📦 股票池：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        df = get_twse_data(s)

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
        st.error("沒有資料（TWSE API異常）")
        st.stop()

    df = df.sort_values("Score", ascending=False)

    st.subheader("🔥 Top 10 強勢股（穩定版）")

    st.dataframe(df.head(10))

    st.bar_chart(df.head(10).set_index("股票")["Score"])
