import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

st.set_page_config(page_title="Trading System", layout="wide")

st.title("🏛️ 穩定量化選股系統")

top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 📊 股票池（穩定版）
# =========================
@st.cache_data(ttl=3600)
def get_stocks():
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        data = requests.get(url, timeout=10).json()
        return [f"{i['Code']}.TW" for i in data][:100]
    except:
        return ["2330.TW", "2317.TW", "2454.TW"]


# =========================
# 📈 計分模型
# =========================
def score(df):

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df = df.dropna()

    if len(df) == 0:
        return 0.5

    bias = (df["Close"].iloc[-1] - df["ma20"].iloc[-1]) / df["ma20"].iloc[-1]

    return float(0.5 + bias)


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 開始掃描"):

    stocks = get_stocks()

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="3mo", progress=False)

            if df is None or df.empty:
                continue

            s_score = score(df)

            results.append({
                "股票": s,
                "分數": s_score
            })

        except:
            continue

        progress.progress((i + 1) / len(stocks))

    df = pd.DataFrame(results)

    if df.empty:
        df = pd.DataFrame([{
            "股票": "2330.TW",
            "分數": 0.5
        }])

    st.subheader("📊 選股結果")

    st.dataframe(df.sort_values("分數", ascending=False).head(top_n))
