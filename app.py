import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests

st.set_page_config(page_title="全市場高速選股", layout="wide")

st.title("⚡ 全市場高速選股系統（Professional Fast Scanner）")

top_n = st.slider("顯示前幾名", 5, 20, 10)


# =========================
# 🧠 安全數值
# =========================
def safe(x):
    try:
        return float(np.array(x).item())
    except:
        return np.nan


# =========================
# 📊 1️⃣ 抓全市場股票（TWSE + TPEX）
# =========================
def get_all_stocks():

    stocks = []

    try:
        # 上市
        url1 = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        data1 = requests.get(url1, timeout=10).json()

        for i in data1:
            stocks.append(f"{i['Code']}.TW")

        # 上櫃
        url2 = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        data2 = requests.get(url2, timeout=10).json()

        for i in data2:
            if "code" in i:
                stocks.append(f"{i['code']}.TWO")

    except:
        pass

    return stocks


# =========================
# ⚡ 2️⃣ 快速過濾（超重要）
# =========================
def quick_filter(df):

    try:
        if df is None or df.empty or len(df) < 60:
            return False

        vol = df["Volume"].iloc[-1]
        vol_ma = df["Volume"].rolling(5).mean().iloc[-1]

        close = df["Close"].iloc[-1]
        ma20 = df["Close"].rolling(20).mean().iloc[-1]

        if np.isnan(vol) or np.isnan(ma20):
            return False

        # 🔥 只留「有動能的股票」
        if vol < vol_ma:
            return False

        if close < ma20 * 0.8:  # 太弱不看
            return False

        return True

    except:
        return False


# =========================
# 📊 3️⃣ 正式打分
# =========================
def score(df):

    try:
        i = len(df) - 1

        close = safe(df["Close"].iloc[i])
        ma20 = safe(df["Close"].rolling(20).mean().iloc[i])
        vol = safe(df["Volume"].iloc[i])
        vol_ma = safe(df["Volume"].rolling(5).mean().iloc[i])

        if np.isnan(close) or np.isnan(ma20) or ma20 == 0:
            return None

        bias = ((close - ma20) / ma20) * 100

        s = 0

        if -25 < bias < -5:
            s += 25

        if vol > vol_ma:
            s += 25

        if close > df["Close"].rolling(60).mean().iloc[i]:
            s += 25

        if close > df["High"].rolling(20).max().iloc[i-1]:
            s += 25

        return {
            "score": s,
            "bias": bias,
            "price": close
        }

    except:
        return None


# =========================
# 🚀 主掃描
# =========================
if st.button("⚡ 開始全市場高速掃描"):

    all_stocks = get_all_stocks()

    st.write(f"總股票數：{len(all_stocks)}")

    results = []
    progress = st.progress(0)

    # 🔥 限制第一階段掃描數（高速關鍵）
    sample = all_stocks[:800]

    filtered = []

    # =========================
    # ⚡ Step1：快篩（很重要）
    # =========================
    for i, s in enumerate(sample):

        try:
            df = yf.download(s, period="3mo", progress=False, threads=True)

            if quick_filter(df):
                filtered.append((s, df))

        except:
            pass

        progress.progress((i + 1) / len(sample))

    st.write(f"快篩後股票：{len(filtered)} 檔")

    # =========================
    # ⚡ Step2：精算
    # =========================
    final = []

    for s, df in filtered:

        r = score(df)

        if r:
            final.append({
                "股票": s,
                "分數": r["score"],
                "乖離%": round(r["bias"], 2),
                "價格": round(r["price"], 2)
            })

    df_result = pd.DataFrame(final)

    if df_result.empty:
        st.warning("沒有符合條件的股票")
    else:
        df_result = df_result.sort_values("分數", ascending=False)

        st.subheader("🏆 Top 選股")
        st.dataframe(df_result.head(top_n))

        st.subheader("📊 分數分布")
        st.bar_chart(df_result.set_index("股票")["分數"])
