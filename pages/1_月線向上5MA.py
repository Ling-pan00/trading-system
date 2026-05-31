import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np

st.set_page_config(page_title="三池量化 Pro v1", layout="wide")
st.title("📊 三池量化交易系統 Pro v1")

# =========================
# 股票池
# =========================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
                stocks.append({
                    "code": code,
                    "name": info.name,
                    "ticker": ticker
                })
    return stocks


stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

st.write(f"📦 股票數：{len(tickers)}")

# =========================
# 技術指標
# =========================
def calc_indicators(df):
    close = df["Close"]
    volume = df["Volume"]

    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()
    vol_ma5 = volume.rolling(5).mean()

    return ma5, ma10, ma20, vol_ma5


# =========================
# 分數模型
# =========================
def score(price, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    if price > ma5: s += 2
    if ma5 > ma10: s += 1
    if ma10 > ma20: s += 1
    if vol > vol_ma5: s += 2
    if change_pct > 0: s += 1
    return s


# =========================
# 型態模型
# =========================
def trend_ok(ma5, ma10, ma20, price):
    return ma5 > ma10 > ma20 and price > ma20


# =========================
# 三池分類（融合）
# =========================
def classify_pool(score_val, trend):
    if score_val >= 6 and trend:
        return "🔴 第三池（主升）"
    elif score_val >= 4:
        return "🟠 第二池（轉強）"
    else:
        return "🟡 第一池（觀察）"


# =========================
# 進出場訊號
# =========================
def signal(price, ma5, vol, vol_ma5):
    if price > ma5 and vol > vol_ma5:
        return "🟢 BUY"
    elif price > ma5:
        return "🟡 HOLD"
    else:
        return "🔴 EXIT"


# =========================
# 回測（核心完整版）
# =========================
def backtest(df, fee=0.001425, slippage=0.001):

    cash = 1.0
    position = 0
    entry = 0

    equity_curve = []

    for i in range(20, len(df)-1):

        price = df["Close"].iloc[i]
        next_price = df["Close"].iloc[i+1]

        ma5 = df["Close"].rolling(5).mean().iloc[i]
        ma10 = df["Close"].rolling(10).mean().iloc[i]
        ma20 = df["Close"].rolling(20).mean().iloc[i]

        vol = df["Volume"].iloc[i]
        vol_ma5 = df["Volume"].rolling(5).mean().iloc[i]

        change_pct = (price - df["Close"].iloc[i-1]) / df["Close"].iloc[i-1]

        s = score(price, ma5, ma10, ma20, vol, vol_ma5, change_pct)
        trend = trend_ok(ma5, ma10, ma20, price)

        pool = classify_pool(s, trend)

        # =========================
        # 進場
        # =========================
        if position == 0 and "第三池" in pool:
            position = cash / price * (1 - fee - slippage)
            entry = price
            cash = 0

        # =========================
        # 出場
        elif position > 0:

            if price < ma5 or "第一池" in pool:
                cash = position * price * (1 - fee - slippage)
                position = 0

        # equity
        total = cash + position * price
        equity_curve.append(total)

    # =========================
    # 指標
    # =========================
    equity = pd.Series(equity_curve)

    returns = equity.pct_change().dropna()

    win_rate = (returns > 0).mean()
    total_return = equity.iloc[-1] - 1
    max_dd = (equity / equity.cummax() - 1).min()
    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() != 0 else 0

    return {
        "win_rate": win_rate,
        "total_return": total_return,
        "max_drawdown": max_dd,
        "sharpe": sharpe
    }


# =========================
# 主選股
# =========================
if st.button("🚀 盤後選股 + 回測"):

    results = []

    batch_size = 150
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    progress = st.progress(0)

    for i in range(total_batches):

        batch = tickers[i*batch_size:(i+1)*batch_size]

        try:
            data = yf.download(
                tickers=batch,
                period="6mo",
                interval="1d",
                group_by="ticker",
                progress=False
            )

            for t in batch:

                try:
                    df = data[t]
                    if df.empty or len(df) < 60:
                        continue

                    ma5, ma10, ma20, vol_ma5 = calc_indicators(df)

                    price = df["Close"].iloc[-1]

                    if price <= ma20.iloc[-1]:
                        continue

                    change_pct = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]

                    s = score(
                        price,
                        ma5.iloc[-1],
                        ma10.iloc[-1],
                        ma20.iloc[-1],
                        df["Volume"].iloc[-1],
                        vol_ma5.iloc[-1],
                        change_pct
                    )

                    trend = trend_ok(
                        ma5.iloc[-1],
                        ma10.iloc[-1],
                        ma20.iloc[-1],
                        price
                    )

                    pool = classify_pool(s, trend)

                    bt = backtest(df)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "分數": s,
                        "池別": pool,
                        "收盤": price,
                        "勝率": round(bt["win_rate"], 3),
                        "報酬": round(bt["total_return"], 3),
                        "最大回撤": round(bt["max_drawdown"], 3),
                        "Sharpe": round(bt["sharpe"], 2)
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i+1)/total_batches)

    df = pd.DataFrame(results)

    # =========================
    # 排名系統（核心升級）
    # =========================
    df["rank_score"] = (
        df["分數"] * 2 +
        df["Sharpe"] * 3 +
        df["勝率"] * 2 +
        df["報酬"] * 3 +
        (1 + df["最大回撤"])
    )

    df = df.sort_values("rank_score", ascending=False)

    # =========================
    # 三池
    # =========================
    pool1 = df[df["池別"].str.contains("第一")].head(10)
    pool2 = df[df["池別"].str.contains("第二")].head(10)
    pool3 = df[df["池別"].str.contains("第三")].head(10)

    st.subheader("🏆 Top Rank（最值得交易）")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("🔴 第三池")
    st.dataframe(pool3, use_container_width=True)

    st.subheader("🟠 第二池")
    st.dataframe(pool2, use_container_width=True)

    st.subheader("🟡 第一池")
    st.dataframe(pool1, use_container_width=True)

    # =========================
    # 績效摘要
    # =========================
    st.subheader("📊 系統績效摘要")

    st.write({
        "平均勝率": round(df["勝率"].mean(), 3),
        "平均報酬": round(df["報酬"].mean(), 3),
        "平均Sharpe": round(df["Sharpe"].mean(), 2),
        "平均回撤": round(df["最大回撤"].mean(), 3),
    })
