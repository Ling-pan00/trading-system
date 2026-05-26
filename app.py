import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px

from sklearn.ensemble import RandomForestClassifier

import warnings
warnings.filterwarnings("ignore")

# =====================================
# 基本設定
# =====================================

INITIAL_CAPITAL = 1_000_000
TOP_N = 5
HOLD_DAYS = 5

FEE_RATE = 0.001425 * 0.28
TAX_RATE = 0.003
SLIPPAGE = 0.001

START_DATE = "2020-01-01"

# =====================================
# 台股池
# =====================================

STOCKS = [
    "2330.TW",
    "2317.TW",
    "2454.TW",
    "2308.TW",
    "2881.TW",
    "2882.TW",
    "1301.TW",
    "1303.TW",
    "2002.TW",
]

# =====================================
# 市場溫度
# =====================================

def get_market_regime():

    try:

        twii = yf.download(
            "^TWII",
            start=START_DATE,
            progress=False
        )

        twii["MA20"] = twii["Close"].rolling(20).mean()
        twii["MA60"] = twii["Close"].rolling(60).mean()

        latest = twii.iloc[-1]

        if latest["MA20"] > latest["MA60"]:
            return "BULL"

        elif latest["MA20"] < latest["MA60"]:
            return "BEAR"

        return "SIDEWAYS"

    except:
        return "SIDEWAYS"

# =====================================
# 技術指標
# =====================================

def calculate_features(df):

    df = df.copy()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()

    df["VolumeMA20"] = (
        df["Volume"].rolling(20).mean()
    )

    df["Bias20"] = (
        (df["Close"] - df["MA20"])
        / df["MA20"]
    )

    df["Volatility"] = (
        df["Close"].pct_change().rolling(20).std()
    )

    df["Return5"] = (
        df["Close"].shift(-5)
        / df["Close"]
        - 1
    )

    df["Target"] = (
        df["Return5"] > 0
    ).astype(int)

    df = df.ffill()
    df = df.dropna()

    return df

# =====================================
# 抓股票資料
# =====================================

def get_stock_data(stock_id):

    try:

        df = yf.download(
            stock_id,
            start=START_DATE,
            progress=False
        )

        if len(df) < 120:
            return None

        df = calculate_features(df)

        return df

    except:
        return None

# =====================================
# AI 模型
# =====================================

def train_model(df):

    FEATURES = [
        "MA20",
        "MA60",
        "VolumeMA20",
        "Bias20",
        "Volatility"
    ]

    try:

        X = df[FEATURES]
        y = df["Target"]

        if len(X) < 100:
            return None

        split = int(len(X) * 0.8)

        X_train = X.iloc[:split]
        y_train = y.iloc[:split]

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=6,
            random_state=42
        )

        model.fit(X_train, y_train)

        return model

    except:
        return None

# =====================================
# AI 分數
# =====================================

def predict_score(model, df):

    FEATURES = [
        "MA20",
        "MA60",
        "VolumeMA20",
        "Bias20",
        "Volatility"
    ]

    try:

        latest_x = df[FEATURES].iloc[-1:]

        score = model.predict_proba(latest_x)[0][1]

        return score

    except:
        return 0.5

# =====================================
# 回測
# =====================================

def run_backtest():

    regime = get_market_regime()

    results = []

    stock_data = {}

    for stock in STOCKS:

        df = get_stock_data(stock)

        if df is None:
            continue

        model = train_model(df)

        if model is None:
            continue

        score = predict_score(model, df)

        stock_data[stock] = {
            "df": df,
            "score": score
        }

    # fallback
    if len(stock_data) == 0:
        return None

    ranked = sorted(
        stock_data.items(),
        key=lambda x: x[1]["score"],
        reverse=True
    )

    # ==========================
    # 空頭減少持股
    # ==========================

    if regime == "BEAR":
        selected = ranked[:2]

    elif regime == "SIDEWAYS":
        selected = ranked[:3]

    else:
        selected = ranked[:TOP_N]

    capital = INITIAL_CAPITAL

    equity_curve = [capital]

    trade_logs = []

    allocation = capital / len(selected)

    for stock, data in selected:

        try:

            df = data["df"]

            buy_price = df["Close"].iloc[-HOLD_DAYS-1]
            sell_price = df["Close"].iloc[-1]

            shares = allocation / buy_price

            buy_cost = (
                buy_price
                * shares
                * (FEE_RATE + SLIPPAGE)
            )

            sell_cost = (
                sell_price
                * shares
                * (FEE_RATE + TAX_RATE + SLIPPAGE)
            )

            gross_profit = (
                (sell_price - buy_price)
                * shares
            )

            net_profit = (
                gross_profit
                - buy_cost
                - sell_cost
            )

            capital += net_profit

            equity_curve.append(capital)

            trade_logs.append({

                "Stock": stock,
                "Buy": round(float(buy_price), 2),
                "Sell": round(float(sell_price), 2),
                "Profit": round(float(net_profit), 0),
                "AI_Score": round(float(data["score"]), 3)

            })

        except:
            continue

    # =====================================
    # 績效
    # =====================================

    equity_series = pd.Series(equity_curve)

    returns = equity_series.pct_change().dropna()

    total_return = (
        capital / INITIAL_CAPITAL
        - 1
    )

    years = 5

    CAGR = (
        (capital / INITIAL_CAPITAL)
        ** (1 / years)
        - 1
    )

    sharpe = 0

    if returns.std() != 0:

        sharpe = (
            returns.mean()
            / returns.std()
        ) * np.sqrt(252)

    rolling_max = equity_series.cummax()

    drawdown = (
        equity_series - rolling_max
    ) / rolling_max

    mdd = drawdown.min()

    win_rate = (
        len([
            t for t in trade_logs
            if t["Profit"] > 0
        ])
        / len(trade_logs)
    ) if len(trade_logs) > 0 else 0

    return {

        "Regime": regime,
        "Capital": capital,
        "TotalReturn": total_return,
        "CAGR": CAGR,
        "Sharpe": sharpe,
        "MDD": mdd,
        "WinRate": win_rate,
        "Trades": pd.DataFrame(trade_logs),
        "Equity": equity_curve

    }

# =====================================
# Streamlit UI
# =====================================

st.set_page_config(
    page_title="台股量化系統",
    layout="wide"
)

st.title("🏛️ 台股 AI 量化交易系統")

if st.button("開始回測"):

    with st.spinner("系統運算中..."):

        result = run_backtest()

    if result is None:

        st.error("無有效資料")

    else:

        # ==========================
        # 市場狀態
        # ==========================

        st.subheader("市場狀態")

        st.success(result["Regime"])

        # ==========================
        # 績效指標
        # ==========================

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "總報酬",
            f"{result['TotalReturn']:.2%}"
        )

        col2.metric(
            "Sharpe",
            f"{result['Sharpe']:.2f}"
        )

        col3.metric(
            "MDD",
            f"{result['MDD']:.2%}"
        )

        col4, col5 = st.columns(2)

        col4.metric(
            "CAGR",
            f"{result['CAGR']:.2%}"
        )

        col5.metric(
            "勝率",
            f"{result['WinRate']:.2%}"
        )

        # ==========================
        # 交易紀錄
        # ==========================

        st.subheader("交易紀錄")

        st.dataframe(result["Trades"])

        # ==========================
        # 資金曲線
        # ==========================

        st.subheader("資金曲線")

        equity_df = pd.DataFrame({
            "Equity": result["Equity"]
        })

        fig = px.line(
            equity_df,
            y="Equity"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        st.success("回測完成")
