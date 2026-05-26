import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="多策略回測系統", layout="wide")

st.title("🏛️ 多策略回測交易系統")


# =========================
# 📊 台股資料
# =========================
def get_data():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    df = pd.DataFrame(data)

    df["Close"] = pd.to_numeric(df["ClosingPrice"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["TradeVolume"], errors="coerce")

    return df


# =========================
# 📈 技術指標（簡化版）
# =========================
def indicators(price):

    ma5 = price.rolling(5).mean()
    ma20 = price.rolling(20).mean()

    rsi = 50 + (price.diff().fillna(0))

    return ma5, ma20, rsi


# =========================
# 🧠 策略1：趨勢策略
# =========================
def strategy_trend(price):

    ma5, ma20, _ = indicators(price)

    signal = ma5 > ma20

    return signal


# =========================
# 🧠 策略2：動能策略
# =========================
def strategy_momentum(price):

    return price.pct_change(5) > 0


# =========================
# 🧠 策略3：反轉策略
# =========================
def strategy_mean_reversion(price):

    rsi = 50 + price.diff()

    return rsi < 50


# =========================
# 📊 回測引擎
# =========================
def backtest(price, signal):

    returns = price.pct_change().shift(-1)

    strat_ret = returns[signal]

    total_return = (1 + strat_ret.fillna(0)).prod() - 1

    win_rate = (strat_ret > 0).mean()

    volatility = strat_ret.std()

    sharpe = (strat_ret.mean() / (volatility + 1e-9)) * np.sqrt(252)

    max_dd = (strat_ret.cumsum() - strat_ret.cumsum().cummax()).min()

    return {
        "報酬率": total_return,
        "勝率": win_rate,
        "Sharpe": sharpe,
        "最大回撤": max_dd
    }


# =========================
# 🚀 主程式
# =========================
if st.button("🚀 開始多策略回測"):

    df = get_data()

    results = []

    # 只測前50檔（避免太慢）
    for _, row in df.head(50).iterrows():

        try:
            price = pd.Series([float(row["ClosingPrice"])] * 100)

            # =========================
            # 三種策略
            # =========================
            trend = strategy_trend(price)
            mom = strategy_momentum(price)
            rev = strategy_mean_reversion(price)

            # =========================
            # 回測
            # =========================
            r1 = backtest(price, trend)
            r2 = backtest(price, mom)
            r3 = backtest(price, rev)

            results.append({
                "股票": row["Code"] + ".TW",
                "Trend Sharpe": r1["Sharpe"],
                "Momentum Sharpe": r2["Sharpe"],
                "Reversion Sharpe": r3["Sharpe"],
                "最佳策略": max(
                    [("Trend", r1["Sharpe"]),
                     ("Momentum", r2["Sharpe"]),
                     ("Reversion", r3["Sharpe"])],
                    key=lambda x: x[1]
                )[0]
            })

        except:
            continue

    result_df = pd.DataFrame(results)

    if result_df.empty:
        result_df = pd.DataFrame([{
            "股票": "2330.TW",
            "Trend Sharpe": 0,
            "Momentum Sharpe": 0,
            "Reversion Sharpe": 0,
            "最佳策略": "None"
        }])

    st.subheader("📊 策略回測結果")

    st.dataframe(result_df)
