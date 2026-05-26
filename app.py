import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="台股策略回測系統", layout="wide")

st.title("📊 台股策略回測系統（穩定終極版）")

stocks = ["2330.TW", "2317.TW", "2454.TW", "2382.TW"]

holding_days = st.slider("持有天數", 1, 10, 5)
stop_loss = st.slider("停損 (%)", -10, -1, -2)
take_profit = st.slider("停利 (%)", 1, 20, 5)


# =========================
# 🧠 安全數值轉換（核心）
# =========================
def safe_float(x):
    try:
        return float(np.array(x).item())
    except:
        return np.nan


# =========================
# 📉 REVERSAL（穩定版）
# =========================
def reversal(df, i):

    if i < 60:
        return False

    ma20 = df["Close"].rolling(20).mean().iloc[i]

    try:
        ma20 = float(ma20)
    except:
        return False

    close = safe_float(df["Close"].iloc[i])

    if np.isnan(close) or np.isnan(ma20) or ma20 == 0:
        return False

    bias = ((close - ma20) / ma20) * 100

    cond1 = -20 < bias < -8
    cond2 = df["Low"].iloc[i] >= df["Low"].iloc[i - 1]
    cond3 = df["Volume"].iloc[i] > df["Volume"].rolling(5).mean().iloc[i]

    return cond1 and cond2 and cond3


# =========================
# 📈 TREND（穩定版）
# =========================
def trend(df, i):

    if i < 60:
        return False

    high20 = df["High"].rolling(20).max().iloc[i - 1]

    try:
        high20 = float(high20)
    except:
        return False

    cond1 = safe_float(df["Close"].iloc[i]) > high20
    cond2 = df["Volume"].iloc[i] > df["Volume"].rolling(20).mean().iloc[i]

    return cond1 and cond2


# =========================
# 🚀 回測主程式
# =========================
if st.button("🚀 開始回測"):

    results = []
    progress = st.progress(0)

    for idx, s in enumerate(stocks):

        df = yf.download(s, period="1y", progress=False)

        if df is None or df.empty or len(df) < 120:
            continue

        for i in range(60, len(df) - holding_days):

            entry_price = safe_float(df["Close"].iloc[i])

            if np.isnan(entry_price):
                continue

            exit_price = None

            # =========================
            # 出場邏輯（停利 / 停損）
            # =========================
            for j in range(i + 1, i + holding_days):

                high = safe_float(df["High"].iloc[j])
                low = safe_float(df["Low"].iloc[j])

                if np.isnan(high) or np.isnan(low):
                    continue

                # 停利
                if (high - entry_price) / entry_price * 100 >= take_profit:
                    exit_price = entry_price * (1 + take_profit / 100)
                    break

                # 停損
                if (low - entry_price) / entry_price * 100 <= stop_loss:
                    exit_price = entry_price * (1 + stop_loss / 100)
                    break

            if exit_price is None:
                exit_price = safe_float(df["Close"].iloc[i + holding_days])

            if np.isnan(exit_price):
                continue

            ret = (exit_price - entry_price) / entry_price * 100

            # =========================
            # REVERSAL
            # =========================
            if reversal(df, i):
                results.append({
                    "股票": s,
                    "策略": "REVERSAL",
                    "進場": round(entry_price, 2),
                    "出場": round(exit_price, 2),
                    "報酬%": round(ret, 2)
                })

            # =========================
            # TREND
            # =========================
            if trend(df, i):
                results.append({
                    "股票": s,
                    "策略": "TREND",
                    "進場": round(entry_price, 2),
                    "出場": round(exit_price, 2),
                    "報酬%": round(ret, 2)
                })

        progress.progress((idx + 1) / len(stocks))

    df_result = pd.DataFrame(results)

    if df_result.empty:
        st.warning("沒有交易訊號")
    else:

        st.subheader("📋 回測明細")
        st.dataframe(df_result)

        st.subheader("📊 策略統計")

        summary = df_result.groupby("策略")["報酬%"].agg([
            "count",
            "mean",
            lambda x: (x > 0).mean()
        ])

        summary.columns = ["交易次數", "平均報酬%", "勝率"]

        st.dataframe(summary)

        st.bar_chart(summary["平均報酬%"])
