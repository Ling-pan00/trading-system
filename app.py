import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="最終回測勝率系統", layout="wide")

st.title("🏛️ AI回測勝率 + 市場溫度 最終版系統")

top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 📌 股票池
# =========================
def get_stocks():
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()
    return [f"{i['Code']}.TW" for i in data]


# =========================
# 🌡️ 市場溫度
# =========================
def market_heat(stocks):

    up = 0
    total = 0

    for s in stocks[:50]:
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
            pass

    ratio = up / total if total > 0 else 0

    if ratio > 0.6:
        return "🟢 多頭市場"
    elif ratio > 0.45:
        return "🟡 盤整市場"
    else:
        return "🔴 空頭市場"


# =========================
# 📊 特徵 + 回測標籤
# =========================
def build_data(df):

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma"] = df["Volume"].rolling(5).mean()

    df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

    # 🎯 未來5日報酬
    df["future"] = df["Close"].shift(-5) / df["Close"] - 1

    # 👉 勝負標籤
    df["label"] = (df["future"] > 0).astype(int)

    df = df.dropna()

    if len(df) < 80:
        return None

    X = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]]
    y = df["label"]

    return X, y, df


# =========================
# 🧠 AI模型
# =========================
def train_model(X, y):

    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=6,
        random_state=42
    )

    model.fit(X, y)

    return model


# =========================
# 📊 預測勝率
# =========================
def predict(model, df):

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma"] = df["Volume"].rolling(5).mean()
    df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

    df = df.dropna()

    if len(df) == 0:
        return None

    latest = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]].iloc[-1]

    prob = model.predict_proba([latest])[0][1]

    return prob


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 開始最終回測系統"):

    stocks = get_stocks()
    stocks = stocks[:120]   # ⚡ 控制速度

    heat = market_heat(stocks)

    st.subheader(f"🌡️ 市場狀態：{heat}")

    X_all = []
    y_all = []

    results = []

    progress = st.progress(0)

    # =========================
    # 🧠 建模型資料
    # =========================
    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            data = build_data(df)

            if data is None:
                continue

            X, y, raw = data

            X_all.append(X)
            y_all.append(y)

        except:
            pass

        progress.progress((i + 1) / len(stocks))

    if len(X_all) == 0:
        st.error("❌ 無法建立模型")
        st.stop()

    X_train = pd.concat(X_all)
    y_train = pd.concat(y_all)

    model = train_model(X_train, y_train)

    st.success("✅ AI模型完成訓練")

    # =========================
    # 📊 預測
    # =========================
    for s in stocks:

        try:
            df = yf.download(s, period="6mo", progress=False)

            if df is None or df.empty:
                continue

            prob = predict(model, df)

            if prob is None:
                continue

            results.append({
                "股票": s,
                "AI勝率": round(prob * 100, 2)
            })

        except:
            pass

        progress.progress(min(1.0, progress.n / len(stocks)))

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有結果")
    else:

        df = df.sort_values("AI勝率", ascending=False)

        st.subheader("🟢 高勝率股票")

        st.dataframe(df.head(top_n))

        st.subheader("📊 勝率分布")
        st.bar_chart(df.set_index("股票")["AI勝率"])
