import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np

st.set_page_config(page_title="三池量化 Pro v1.3", layout="wide")
st.title("📊 三池量化交易系統 Pro v1.3（第一池修正版）")

# =========================
# 股票池
# =========================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []

    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():

                ticker = (
                    f"{code}.TW"
                    if info.market == "上市"
                    else f"{code}.TWO"
                )

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
    s += 2 if price > ma5 else 0
    s += 1 if ma5 > ma10 else 0
    s += 1 if ma10 > ma20 else 0
    s += 2 if vol > vol_ma5 else 0
    s += 1 if change_pct > 0 else 0
    return s


# =========================
# 三池分類（🔥第一池已修正版）
# =========================
def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    # 月線向上
    if len(df) < 25:
        return None

    month_up = df["ma20"].iloc[-1] > df["ma20"].iloc[-5]

    # 股價在月線上
    above_ma20 = price > ma20

    # 曾跌破5MA（洗盤）
    dipped = (df["Low"].iloc[-10:] < df["ma5"].iloc[-10:]).any()

    # 剛站回5MA（關鍵轉折）
    reclaim_ma5 = (
        price > ma5 and
        df["Close"].iloc[-2] <= df["ma5"].iloc[-2]
    )

    # 紅K
    red_k = price > open_price

    # 🟡 第一池（修正版）
    pool1 = month_up and above_ma20 and dipped and reclaim_ma5 and red_k

    # 🟠 第二池
    pool2 = month_up and above_ma20 and s >= 4

    # 🔴 第三池
    pool3 = month_up and above_ma20 and s >= 6 and ma5 > ma10 > ma20

    if pool3:
        return "🔴 第三池"
    elif pool2:
        return "🟠 第二池"
    elif pool1:
        return "🟡 第一池"
    else:
        return None


# =========================
# 進出場模型
# =========================
def trade_levels(price, ma5, ma10, pool):

    entry = price

    if pool == "🔴 第三池":
        stop = ma10
        target = price * 1.25
    elif pool == "🟠 第二池":
        stop = ma5
        target = price * 1.20
    else:
        stop = ma5
        target = price * 1.12

    return round(entry, 2), round(stop, 2), round(target, 2)


# =========================
# 🚀 盤後選股
# =========================
if st.button("🚀 盤後選股"):

    results = []
    batch_size = 200

    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)

    for i in range(total_batches):

        batch = tickers[i * batch_size:(i + 1) * batch_size]

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
                    open_price = df["Open"].iloc[-1]

                    ma5 = df["ma5"].iloc[-1]
                    ma10 = df["ma10"].iloc[-1]
                    ma20 = df["ma20"].iloc[-1]

                    if pd.isna(ma20):
                        continue

                    change_pct = (df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2]

                    s = score(
                        price, ma5, ma10, ma20,
                        df["Volume"].iloc[-1],
                        df["vol_ma5"].iloc[-1],
                        change_pct
                    )

                    pool = classify_pool(
                        s, df, price, ma5, ma10, ma20, open_price
                    )

                    if pool is None:
                        continue

                    entry, stop, target = trade_levels(price, ma5, ma10, pool)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "分數": s,
                        "池別": pool,
                        "收盤": round(price, 2),
                        "進場價": entry,
                        "停損價": stop,
                        "目標價": target
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i + 1) / total_batches)

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有符合條件股票")

    else:
        df = df.sort_values("分數", ascending=False)

        st.subheader("🏆 Top 20")
        st.dataframe(df.head(20), use_container_width=True)

        st.subheader("🔴 第三池")
        st.dataframe(df[df["池別"] == "🔴 第三池"].head(10))

        st.subheader("🟠 第二池")
        st.dataframe(df[df["池別"] == "🟠 第二池"].head(10))

        st.subheader("🟡 第一池")
        st.dataframe(df[df["池別"] == "🟡 第一池"].head(10))

        st.session_state["pool1"] = df[df["池別"] == "🟡 第一池"]
        st.session_state["pool2"] = df[df["池別"] == "🟠 第二池"]
        st.session_state["pool3"] = df[df["池別"] == "🔴 第三池"]


# =========================
# 📈 盤中監控
# =========================
st.subheader("📈 盤中監控")


def run_monitor(df):

    live = []

    for _, row in df.iterrows():

        try:
            t = row["ticker"]

            data = yf.download(t, period="10d", interval="1d", progress=False)

            if data is None or len(data) < 6:
                continue

            close = data["Close"]
            volume = data["Volume"]

            open_now = data["Open"].iloc[-1]
            close_now = close.iloc[-1]

            ma5 = close.rolling(5).mean().iloc[-1]

            high_5 = data["High"].iloc[-6:-1].max()

            vol_today = volume.iloc[-1]
            vol_avg = volume.rolling(5).mean().iloc[-1]

            red_k = close_now > open_now
            above_ma5 = close_now > ma5
            breakout = close_now > high_5
            vol_ok = vol_today > vol_avg

            if red_k and above_ma5 and vol_ok and breakout:
                signal = "🟢 強力BUY"
            elif red_k and above_ma5:
                signal = "🟡 WATCH"
            else:
                signal = "🔴 NO"

            live.append({
                "代號": row["代號"],
                "名稱": row["名稱"],
                "池別": row["池別"],
                "收盤": round(close_now, 2),
                "MA5": round(ma5, 2),
                "紅K": "✅" if red_k else "❌",
                "站上MA5": "✅" if above_ma5 else "❌",
                "量能": "✅" if vol_ok else "❌",
                "突破": "✅" if breakout else "❌",
                "訊號": signal
            })

        except:
            continue

    return pd.DataFrame(live)


if st.button("🔄 更新盤中監控"):

    if "pool1" not in st.session_state:
        st.warning("請先執行盤後選股")
        st.stop()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🟡 第一池")
        st.dataframe(run_monitor(st.session_state["pool1"]), use_container_width=True)

    with col2:
        st.markdown("### 🟠 第二池")
        st.dataframe(run_monitor(st.session_state["pool2"]), use_container_width=True)

    with col3:
        st.markdown("### 🔴 第三池")
        st.dataframe(run_monitor(st.session_state["pool3"]), use_container_width=True)
