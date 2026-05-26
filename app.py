import streamlit as st
import pandas as pd
import numpy as np
import requests

from universe import build_universe


st.title("🏛️ 穩定法人 Top10（TWSE修正版）")


# =========================
# 📊 TWSE 安全抓資料
# =========================
def get_twse_data(stock_code):

    try:
        code = stock_code.replace(".TW", "")

        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        params = {
            "stockNo": code,
            "response": "json"
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        # 🚨 檢查 API 是否成功
        if data.get("stat") != "OK":
            return None

        if "data" not in data:
            return None

        df = pd.DataFrame(data["data"], columns=data["fields"])

        # 🚨 防止 "-" / 空值
        df["close"] = (
            df["收盤價"]
            .str.replace(",", "")
            .replace("-", np.nan)
        )

        df = df.dropna(subset=["close"])
        df["close"] = df["close"].astype(float)

        return df

    except:
        return None


# =========================
# 🧠 打分模型（簡化穩定版）
# =========================
def score(df):

    try:
        if len(df) < 10:
            return None

        df = df.copy()

        df["ma5"] = df["close"].rolling(5).mean()
        df["ma10"] = df["close"].rolling(10).mean()

        df = df.dropna()

        if len(df) < 10:
            return None

        momentum = df["close"].iloc[-1] / df["close"].iloc[-5] - 1
        trend = (df["ma5"].iloc[-1] - df["ma10"].iloc[-1]) / df["ma10"].iloc[-1]

        return momentum * 0.6 + trend * 0.4

    except:
        return None


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 產生 Top10"):

    stocks = build_universe(percentile=0.2)

    st.write(f"📦 股票池數量：{len(stocks)}")

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

    # 🚨 保底機制（關鍵）
    if df.empty:
        st.warning("TWSE API不穩，啟用保底股票")

        df = pd.DataFrame([
            {"股票": "2330.TW", "Score": 1},
            {"股票": "2317.TW", "Score": 0.9},
            {"股票": "2454.TW", "Score": 0.8},
        ])

    df = df.sort_values("Score", ascending=False)

    st.subheader("🔥 Top 10")

    st.dataframe(df.head(10))

    st.bar_chart(df.head(10).set_index("股票")["Score"])
