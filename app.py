import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="📊 台股策略回測系統", layout="wide")

st.title("📊 台股策略回測系統（REVERSAL vs TREND）")

stocks = ["2330.TW", "2317.TW", "2454.TW", "2382.TW"]

holding_days = st.slider("持有天數", 1, 10, 5)
stop_loss = st.slider("停損 (%)", -10, -1, -2)
take_profit = st.slider("停利 (%)", 1, 20, 5)


# =========================
# 📉 REVERSAL（跌深反轉）
# =========================
def reversal(df, i):

    if i < 60:
        return False

    ma20 = df["Close"].rolling(20).mean().iloc[i]

    bias = (df["Close"].iloc[i] - ma20) / ma20 * 100

    cond1 = -20 < bias < -8
    cond2 = df["Low"].iloc[i] >= df["Low"].iloc[i-1]
    cond3 = df["Volume"].iloc[i] > df["Volume"].rolling(5).mean().iloc[i]

    return cond1 and cond2 and cond3


# =========================
# 📈 TREND（順勢突破）
# =========================
def trend(df, i):

    if i < 60:
        return False

    high20 = df["High"].rolling(20).max().iloc[i-1]

    cond1 = df["Close"].iloc[i] > high20
    cond2 = df["Volume"].iloc[i] > df["Volume"].rolling(20).mean().iloc[i]

    return cond1 and cond2


# =========================
# 🚀 開始回測
# =========================
if st.button("🚀 開始回測"):

    results = []

    progress = st.progress(0)

    for idx, s in enumerate(stocks):

        df = yf.download(s, period="1y", progress=False)

        if df.empty:
            continue

        for i in range(60, len(df)-holding_days):

            entry_price = df["Close"].iloc[i]

            exit_price = None

            # =========================
            # 停利停損模擬
            # =========================
            for j in range(i+1, i+holding_days):

                high = df["High"].iloc[j]
                low = df["Low"].iloc[j]

                # 停利
                if (high - entry_price) / entry_price * 100 >= take_profit:
                    exit_price = entry_price * (1 + take_profit/100)
                    break

                # 停損
                if (low - entry_price) / entry_price * 100 <= stop_loss:
                    exit_price = entry_price * (1 + stop_loss/100)
                    break

            # 到期出場
            if exit_price is None:
                exit_price = df["Close"].iloc[i+holding_days]

            ret = (exit_price - entry_price) / entry_price * 100

            # =========================
            # REVERSAL
            # =========================
            if reversal(df, i):

                results.append({
                    "股票": s,
                    "策略": "REVERSAL",
                    "進場價": round(float(entry_price), 2),
                    "出場價": round(float(exit_price), 2),
                    "報酬%": round(float(ret), 2)
                })

            # =========================
            # TREND
            # =========================
            if trend(df, i):

                results.append({
                    "股票": s,
                    "策略": "TREND",
                    "進場價": round(float(entry_price), 2),
                    "出場價": round(float(exit_price), 2),
                    "報酬%": round(float(ret), 2)
                })

        progress.progress((idx + 1) / len(stocks))

    result_df = pd.DataFrame(results)

    if result_df.empty:
        st.warning("沒有符合條件的交易訊號")
    else:

        st.subheader("📋 回測明細")
        st.dataframe(result_df)

        # =========================
        # 📊 統計
        # =========================
        summary = result_df.groupby("策略")["報酬%"].agg([
            "count",
            "mean",
            lambda x: (x > 0).mean()
        ])

        summary.columns = [
            "交易次數",
            "平均報酬%",
            "勝率"
        ]

        st.subheader("📊 策略統計")
        st.dataframe(summary)

        st.bar_chart(summary["平均報酬%"])
