import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="實盤交易終極版", layout="wide")

st.title("🏛️ 實盤交易決策終極系統（Production Engine）")

top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 📌 股票池
# =========================
def get_stocks():
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()
    return [f"{i['Code']}.TW" for i in data]


# =========================
# 🌡️ 市場風險開關（核心）
# =========================
def market_regime(stocks):

    up = 0
    total = 0

    for s in stocks[:40]:
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
        return "🟢 多頭（可積極）", 1.2
    elif ratio > 0.45:
        return "🟡 盤整（保守）", 1.0
    else:
        return "🔴 空頭（防守）", 0.7


# =========================
# 📊 特徵工程
# =========================
def features(df):

    if df is None or df.empty or len(df) < 60:
        return None

    df = df.copy()

    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma"] = df["Volume"].rolling(5).mean()

    df["bias"] = (df["Close"] - df["ma20"]) / df["ma20"]

    df = df.dropna()

    if len(df) < 50:
        return None

    X = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]]

    df["future"] = df["Close"].shift(-5) / df["Close"] - 1
    df["label"] = (df["future"] > 0).astype(int)

    df = df.dropna()

    y = df["label"]

    return X, y


# =========================
# 🤖 AI模型
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
        return 0.5

    latest = df[["bias", "Volume", "vol_ma", "ma20", "ma60"]].iloc[-1]

    return model.predict_proba([latest])[0][1]


# =========================
# 🧠 最終決策引擎（核心）
# =========================
def decision(prob, regime_factor):

    score = prob * 100 * regime_factor

    if score >= 75:
        return "🟢 強勢進場"
    elif score >= 60:
        return "🟡 觀察等待"
    else:
        return "🔴 不交易"


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 啟動實盤決策系統"):

    stocks = get_stocks()
    stocks = stocks[:120]

    regime, factor = market_regime(stocks)

    st.subheader(f"🌡️ 市場狀態：{regime}")

    X_all = []
    y_all = []

    results = []

    progress = st.progress(0)

    # =========================
    # 🧠 建模
    # =========================
    for i, s in enumerate(stocks):

        try:
            df = yf.download(s, period="6mo", progress=False)

            f = features(df)

            if f is None:
                continue

            X, y = f

            X_all.append(X)
            y_all.append(y)

        except:
            pass

        progress.progress((i + 1) / len(stocks))

    if len(X_all) == 0:
        st.error("❌ 無法建立模型（資料不足）")
        st.stop()

    X_train = pd.concat(X_all)
    y_train = pd.concat(y_all)

    model = train_model(X_train, y_train)

    st.success("✅ 模型建立完成")

    # =========================
    # 📊 預測
    # =========================
    for s in stocks:

        try:
            df = yf.download(s, period="6mo", progress=False)

            prob = predict(model, df)

            final = decision(prob, factor)

            results.append({
                "股票": s,
                "訊號": final,
                "勝率": round(prob * 100, 2)
            })

        except:
            pass

        progress.progress(min(1.0, progress.n / len(stocks)))

    df = pd.DataFrame(results)

    st.subheader("🟢 強勢標的")
    st.dataframe(df.sort_values("勝率", ascending=False).head(top_n))

    st.subheader("📊 分布")
    st.bar_chart(df.set_index("股票")["勝率"])
