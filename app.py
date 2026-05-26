import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="三層訊號選股系統", layout="wide")

st.title("🏛️ 三層訊號選股系統（Professional Signal Engine）")

# =========================
# 📌 股票池（穩定版）
# =========================
def get_stocks():
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return [f"{i['Code']}.TW" for i in data]


# =========================
# 🧠 安全數值
# =========================
def safe(x):
    try:
        return float(np.array(x).item())
    except:
        return np.nan


# =========================
# 📊 計算指標
# =========================
def analyze(df):

    if df is None or df.empty or len(df) < 120:
        return None

    i = len(df) - 1

    close = safe(df["Close"].iloc[i])
    ma20 = safe(df["Close"].rolling(20).mean().iloc[i])
    ma60 = safe(df["Close"].rolling(60).mean().iloc[i])
    vol = safe(df["Volume"].iloc[i])
    vol_ma = safe(df["Volume"].rolling(5).mean().iloc[i])

    if np.isnan(close) or np.isnan(ma20):
        return None

    bias = ((close - ma20) / ma20) * 100

    strength = 0

    # 📈 趨勢
    if close > ma60:
        strength += 2

    # 📊 量能
    if vol > vol_ma:
        strength += 1

    # 🚀 突破
    if close > df["High"].rolling(20).max().iloc[i-1]:
        strength += 2

    return bias, strength, close


# =========================
# 🧠 三層分類
# =========================
def classify(bias, strength):

    # 🟢 強勢（已發動）
    if strength >= 3 and -20 < bias < 10:
        return "🟢 強勢訊號"

    # 🟡 準備（即將發動）
    if strength >= 1 and -35 < bias < 20:
        return "🟡 準備訊號"

    return "🔴 無訊號"


# =========================
# 🚀 掃描
# =========================
if st.button("🚀 開始三層掃描"):

    stocks = get_stocks()
    stocks = stocks[:600]  # ⚡ 控制速度（可改）

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            r = analyze(df)

            if r is None:
                continue

            bias, strength, price = r
            signal = classify(bias, strength)

            results.append({
                "股票": s,
                "訊號": signal,
                "強度": strength,
                "乖離%": round(bias, 2),
                "價格": round(price, 2)
            })

        except:
            pass

        progress.progress((i + 1) / len(stocks))

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有資料")
    else:

        st.subheader("🟢 強勢訊號")
        st.dataframe(df[df["訊號"] == "🟢 強勢訊號"])

        st.subheader("🟡 準備訊號")
        st.dataframe(df[df["訊號"] == "🟡 準備訊號"])

        st.subheader("📊 全部排序")
        st.dataframe(df.sort_values("強度", ascending=False))
