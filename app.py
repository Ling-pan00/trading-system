import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="完整交易系統架構", layout="wide")

st.title("🏛️ 完整交易系統架構（Institutional Grade）")

top_n = st.slider("顯示前幾名", 5, 20, 10)
capital = st.number_input("模擬資金", value=100000)


# =========================
# 🟢 Universe Layer
# =========================
def get_stocks():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return [f"{i['Code']}.TW" for i in data][:120]


# =========================
# 🌡️ Market Regime
# =========================
def market_regime(stocks):

    up = 0
    total = 0

    for s in stocks[:50]:

        try:
            df = yf.download(s, period="1mo", progress=False)

            if df is None or df.empty:
                continue

            ma20 = df["Close"].rolling(20).mean().iloc[-1]
            close = df["Close"].iloc[-1]

            if np.isnan(ma20):
                continue

            total += 1
            if close > ma20:
                up += 1

        except:
            continue

    ratio = up / total if total > 0 else 0.5

    if ratio > 0.6:
        return "bull"
    elif ratio > 0.45:
        return "sideways"
    else:
        return "bear"


# =========================
# 🟢 Strategy Layer
# =========================
def score_stock(df):

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

    df = df.ffill().dropna()

    if len(df) == 0:
        return 0.5

    return float(df["bias"].iloc[-1] + 0.5)


# =========================
# 🟢 Portfolio Layer（核心）
# =========================
def allocate(df, capital):

    df = df.copy()

    df = df.sort_values("score", ascending=False)

    top = df.head(5)

    weight = 1 / len(top)

    positions = []

    for _, row in top.iterrows():

        alloc = capital * weight

        positions.append({
            "股票": row["stock"],
            "分數": row["score"],
            "資金配置": round(alloc, 2)
        })

    return pd.DataFrame(positions)


# =========================
# 🟢 Execution Layer
# =========================
def run_system():

    stocks = get_stocks()

    regime = market_regime(stocks)

    st.write(f"🌡️ 市場狀態：{regime}")

    results = []

    for s in stocks:

        try:
            df = yf.download(s, period="3mo", progress=False)

            if df is None or df.empty:
                continue

            score = score_stock(df)

            # 🧠 regime 調整（核心）
            if regime == "bull":
                score *= 1.2
            elif regime == "bear":
                score *= 0.8

            results.append({
                "stock": s,
                "score": score
            })

        except:
            continue

    df = pd.DataFrame(results)

    if df.empty:
        df = pd.DataFrame([{
            "stock": "2330.TW",
            "score": 0.5
        }])

    return df


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 啟
