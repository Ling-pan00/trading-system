import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf

st.set_page_config(page_title="法人 Top10 系統", layout="wide")

st.title("🏛️ 法人級 Top 10 選股系統（穩定版）")


# =========================
# 📊 股票池（乾淨版）
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i.get("Code", "")
        name = i.get("Name", "")

        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        name = str(name)

        # 🚨 ETF / ETN 排除（最重要）
        if any(x in name for x in ["ETF", "ETN", "指數", "槓桿", "反向", "債券"]):
            continue

        # 🚨 台股 ETF 常見區間再保護
        if code.startswith(("00", "006", "008", "009")):
            continue

        stocks.append(code + ".TW")

    return stocks   # ❗不限制數量（重點）


# =========================
# 📈 取得真實價格
# =========================
def get_data(stock):

    try:
        df = yf.download(stock, period="6mo", progress=False)

        if df is None or df.empty:
            return None

        return df

    except:
        return None


# =========================
# 🧠 法人打分模型
# =========================
def score(df):

    try:
        df = df.copy()

        df["ma20"] = df["Close"].rolling(20).mean()
        df["ma60"] = df["Close"].rolling(60).mean()

        df = df.dropna()

        if len(df) < 60:
            return None

        momentum = df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1

        trend = (df["ma20"].iloc[-1] - df["ma60"].iloc[-1]) / df["ma60"].iloc[-1]

        volatility = df["Close"].pct_change().std()

        volume = df["Volume"].mean()

        return (
            momentum * 0.4 +
            trend * 0.3 +
            np.log(volume + 1) * 0.2 +
            volatility * 0.1
        )

    except:
        return None


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 產生 Top 10 訊號"):

    stocks = get_universe()

    # 👉 在這裡控制掃描數量（重點）
    stocks = stocks[:200]   # 🔥 你要 100 / 200 / 300 改這裡

    st.write(f"📦 股票池數量：{len(stocks)}")

    results = []

    progress = st.progress(0)

    for i, s in enumerate(stocks):

        df = get_data(s)

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
        st.warning("沒有可用資料（yfinance 失敗）")
        st.stop()

    df = df.sort_values("Score", ascending=False)

    top10 = df.head(10)

    st.subheader("🔥 Top 10 強勢股票")

    st.dataframe(top10)

    st.bar_chart(top10.set_index("股票")["Score"])
