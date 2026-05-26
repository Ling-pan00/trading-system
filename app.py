import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="永不空訊號系統", layout="wide")

st.title("📊 永不空訊號系統（Signal Always ON Engine）")

top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 📌 股票池
# =========================
def get_stocks():
    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        data = requests.get(url, timeout=10).json()
        return [f"{i['Code']}.TW" for i in data][:120]
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

    if len(df) < 50:
        return None

    df["future"] = df["Close"].shift(-5) / df["Close"] - 1
    df["label"] = (df["future"] > 0).astype(int)

    df = df.dropna()

    X = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]]
    y = df["label"]

    return X, y


# =========================
# 🧠 model
# =========================
def train_model(X, y):

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        random_state=42
    )

    model.fit(X, y)

    return model


# =========================
# 📊 單股訊號分數
# =========================
def score_stock(model, df):

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma"] = df["Volume"].rolling(5).mean()
    df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

    df = df.ffill().dropna()

    if len(df) == 0:
        return 0.5

    latest = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]].iloc[-1]

    prob = model.predict_proba([latest])[0][1]

    return prob


# =========================
# 🌡️ 市場濾網（不會阻斷訊號）
# =========================
def market_filter(stocks):

    up = 0
    total = 0

    for s in stocks[:30]:
        try:
            df = yf.download(s, period="1mo", progress=False)

            if df is None or df.empty:
                continue

            close = df["Close"].iloc[-1]
            ma20 = df["Close"].rolling(20).mean().iloc[-1]

            if np.isnan(ma20):
                continue

            total += 1
            if close > ma20:
                up += 1

        except:
            continue

    ratio = up / total if total > 0 else 0.5

    return ratio


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 啟動永不空訊號系統"):

    stocks = get_stocks()

    ratio = market_filter(stocks)

    st.write(f"🌡️ 市場強度：{round(ratio, 2)}")

    # =========================
    # 🧠 建模資料
    # =========================
    X_all = []
    y_all = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            res = build(df)

            if res is None:
                continue

            X, y = res

            X_all.append(X)
            y_all.append(y)

        except:
            continue

        progress.progress((i + 1) / len(stocks))

    # 🧠 保底（永遠不空）
    if len(X_all) == 0:

        st.warning("啟動 fallback 模型")

        X_all = [pd.DataFrame(np.random.rand(200, 5))]
        y_all = [pd.Series(np.random.randint(0, 2, 200))]

    X_train = pd.concat(X_all)
    y_train = pd.concat(y_all)

    model = train_model(X_train, y_train)

    st.success("✅ 模型建立完成")

    # =========================
    # 📊 訊號輸出（永遠有）
    # =========================
    results = []

    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            prob = score_stock(model, df)

            # 🧠 分級訊號（重點）
            if prob > 0.65:
                signal = "🟢 強勢"
            elif prob > 0.55:
                signal = "🟡 中性"
            else:
                signal = "🔴 弱勢"

            results.append({
                "股票": s,
                "機率": round(prob * 100, 2),
                "訊號": signal
            })

        except:
            continue

        progress.progress(min(1.0, i / len(stocks)))

    df = pd.DataFrame(results)

    # 🧠 永遠保證有輸出
    if df.empty:
        df = pd.DataFrame([{
            "股票": "2330.TW",
            "機率": 50,
            "訊號": "🟡 中性"
        }])

    st.subheader("📊 永不空訊號排行榜")

    st.dataframe(df.sort_values("機率", ascending=False).head(top_n))

    st.subheader("📈 訊號分布")
    st.bar_chart(df.set_index("股票")["機率"])
