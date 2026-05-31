import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np

st.set_page_config(page_title="三池量化 Pro v1.2", layout="wide")
st.title("📊 三池量化交易系統 Pro v1.2（完整進出場版）")

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
def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df


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
# 型態
# =========================
def trend_ok(ma5, ma10, ma20, price):
    return ma5 > ma10 > ma20 and price > ma20


# =========================
# 三池分類
# =========================
def classify_pool(s, trend):
    if s >= 6 and trend:
        return "🔴 第三池"
    elif s >= 4:
        return "🟠 第二池"
    else:
        return "🟡 第一池"


# =========================
# 進出場模型（核心補齊）
# =========================
def trade_levels(price, ma5, ma10, pool):

    entry = price

    # 預設
    stop = price * 0.95
    target = price * 1.15

    if pool == "🟠 第二池":
        stop = ma5
        target = price * 1.2

    elif pool == "🔴 第三池":
        stop = ma10
        target = price * 1.25

    else:
        stop = price * 0.94
        target = price * 1.12

    return round(entry, 2), round(stop, 2), round(target, 2)


# =========================
# 盤中訊號
# =========================
def intraday_signal(open_p, close_y, low_y, high_y, vol, vol_y):

    strong = open_p >= close_y
    hold = open_p >= low_y
    vol_ok = vol >= vol_y * 0.7
    breakout = open_p > high_y

    if strong and hold and vol_ok:
        return "🟢 BUY" if breakout else "🟡 WATCH"
    if hold:
        return "🟡 WATCH"
    return "🔴 NO"


# =========================
# 🚀 盤後選股（快速版）
# =========================
if st.button("🚀 盤後選股"):

    results = []

    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    progress = st.progress(0)

    for i in range(total_batches):

        batch = tickers[i*batch_size:(i+1)*batch_size]

        try:
            data = yf.download(
                tickers=batch,
                period="3mo",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=True
            )

            for t in batch:

                try:
                    df = data[t]
                    if df.empty or len(df) < 30:
                        continue

                    df = add_indicators(df)

                    price = df["Close"].iloc[-1]

                    # 月線濾網
                    if price <= df["ma20"].iloc[-1]:
                        continue

                    change_pct = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]

                    s = score(
                        price,
                        df["ma5"].iloc[-1],
                        df["ma10"].iloc[-1],
                        df["ma20"].iloc[-1],
                        df["Volume"].iloc[-1],
                        df["vol_ma5"].iloc[-1],
                        change_pct
                    )

                    trend = trend_ok(
                        df["ma5"].iloc[-1],
                        df["ma10"].iloc[-1],
                        df["ma20"].iloc[-1],
                        price
                    )

                    pool = classify_pool(s, trend)

                    entry, stop, target = trade_levels(
                        price,
                        df["ma5"].iloc[-1],
                        df["ma10"].iloc[-1],
                        pool
                    )

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "分數": s,
                        "池別": pool,
                        "收盤": price,

                        # ⭐ 進出場
                        "進場價": entry,
                        "停損價": stop,
                        "目標價": target
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i+1)/total_batches)

    df = pd.DataFrame(results)

    df["rank"] = df["分數"]
    df = df.sort_values("rank", ascending=False)

    st.subheader("🏆 Top 20 排名")
    st.dataframe(df.head(20), use_container_width=True)

    st.subheader("🔴 第三池")
    st.dataframe(df[df["池別"]=="🔴 第三池"].head(10))

    st.subheader("🟠 第二池")
    st.dataframe(df[df["池別"]=="🟠 第二池"].head(10))

    st.subheader("🟡 第一池")
    st.dataframe(df[df["池別"]=="🟡 第一池"].head(10))

    st.session_state["pool1"] = df[df["池別"]=="🟡 第一池"]
    st.session_state["pool2"] = df[df["池別"]=="🟠 第二池"]
    st.session_state["pool3"] = df[df["池別"]=="🔴 第三池"]


# =========================
# 📈 盤中監控（完整回來）
# =========================
st.subheader("📈 盤中監控")


def run_monitor(df):

    live = []

    for _, row in df.iterrows():

        try:
            t = row["ticker"]

            data = yf.download(t, period="5d", interval="1d", progress=False)

            if len(data) < 3:
                continue

            close = data["Close"]
            volume = data["Volume"]

            open_now = data["Open"].iloc[-1]
            close_y = close.iloc[-2]
            low_y = data["Low"].min()
            high_y = data["High"].max()

            vol = volume.iloc[-1]
            vol_y = volume.rolling(5).mean().iloc[-1]

            sig = intraday_signal(open_now, close_y, low_y, high_y, vol, vol_y)

            live.append({
                "代號": row["代號"],
                "名稱": row["名稱"],
                "池別": row["池別"],
                "訊號": sig
            })

        except:
            continue

    return pd.DataFrame(live)


if st.button("🔄 更新盤中監控"):

    if "pool1" not in st.session_state:
        st.warning("請先盤後選股")
        st.stop()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🟡 第一池")
        st.dataframe(run_monitor(st.session_state["pool1"]))

    with col2:
        st.markdown("### 🟠 第二池")
        st.dataframe(run_monitor(st.session_state["pool2"]))

    with col3:
        st.markdown("### 🔴 第三池")
        st.dataframe(run_monitor(st.session_state["pool3"]))
