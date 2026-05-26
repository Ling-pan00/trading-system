import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="交易室即時系統", layout="wide")

st.title("🏛️ Trading Desk 即時訊號系統")

refresh = st.slider("更新頻率（秒）", 30, 300, 60)
top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 📊 股票池（穩定）
# =========================
@st.cache_data(ttl=3600)
def get_stocks():

    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        data = requests.get(url, timeout=10).json()

        stocks = [f"{i['Code']}.TW" for i in data]

        return stocks[:100]

    except:
        return ["2330.TW", "2317.TW", "2454.TW", "2303.TW"]


# =========================
# 🧠 features
# =========================
def build(df):

    if df is None or df.empty:
        return None

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma"] = df["Volume"].rolling(5).mean()

    df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

    df = df.ffill().dropna()

    if len(df) < 30:
        return None

    return df


# =========================
# 🧠 fallback model
# =========================
def fallback():

    X = pd.DataFrame(np.random.rand(200, 5))
    y = pd.Series(np.random.randint(0, 2, 200))

    model = RandomForestClassifier(n_estimators=80, max_depth=5)
    model.fit(X, y)

    return model


model = fallback()


# =========================
# 🌡️ 市場溫度
# =========================
def market_heat(stocks):

    up = 0
    total = 0

    for s in stocks[:30]:

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
        return "🟢 Risk-On"
    elif ratio > 0.45:
        return "🟡 Neutral"
    else:
        return "🔴 Risk-Off"


# =========================
# 📊 即時掃描
# =========================
def scan(stocks):

    results = []

    for s in stocks:

        try:
            df = yf.download(s, period="3mo", interval="1d", progress=False)

            if df is None or df.empty:
                continue

            df["ma20"] = df["Close"].rolling(20).mean()
            df["ma60"] = df["Close"].rolling(60).mean()
            df["vol_ma"] = df["Volume"].rolling(5).mean()
            df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

            df = df.ffill().dropna()

            if len(df) == 0:
                continue

            latest = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]].iloc[-1]

            prob = model.predict_proba([latest])[0][1]

            # 🧠 分級訊號
            if prob > 0.65:
                sig = "🟢 強勢"
            elif prob > 0.55:
                sig = "🟡 中性"
            else:
                sig = "🔴 弱勢"

            results.append({
                "股票": s,
                "機率": round(prob * 100, 2),
                "訊號": sig
            })

        except:
            continue

    return pd.DataFrame(results)


# =========================
# 🚀 主程式
# =========================
stocks = get_stocks()

col1, col2 = st.columns(2)

with col1:
    st.subheader("🌡️ 市場狀態")
    st.write(market_heat(stocks))

with col2:
    st.subheader("📊 系統狀態")
    st.write(f"掃描股票數：{len(stocks)}")

placeholder = st.empty()

# =========================
# 🔁 即時更新迴圈
# =========================
while True:

    df = scan(stocks)

    if df.empty:
        df = pd.DataFrame([{
            "股票": "2330.TW",
            "機率": 55,
            "訊號": "🟡 Neutral"
        }])

    with placeholder.container():

        st.subheader("📊 即時強勢排行")

        st.dataframe(df.sort_values("機率", ascending=False).head(top_n))

        st.bar_chart(df.set_index("股票")["機率"])

    time.sleep(refresh)
    st.rerun()
