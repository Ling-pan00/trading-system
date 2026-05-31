import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np

st.set_page_config(page_title="四池量化 Pro v2.1", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.1（穩定完整版）")

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
# 四池分類
# =========================
def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 25:
        return None

    ma20_series = df["ma20"].dropna()
    if len(ma20_series) < 5:
        return None

    # =========================
    # 🟡 第一池（新版本）
    # =========================

    # MA20 不下彎（近5天平均上升）
    ma20_up = df["ma20"].iloc[-1] >= df["ma20"].iloc[-5]

    # 15日內曾跌破 MA5
    washed = (df["Close"].tail(15) < df["ma5"].tail(15)).any()

    # 最新站回 MA5
    reclaim_ma5 = price > ma5

    # 紅K
    red_k = price > open_price

    pool1 = ma20_up and washed and reclaim_ma5 and red_k

    # 🟠 第二池
    month_up = ma20_series.iloc[-1] > ma20_series.iloc[-min(5, len(ma20_series))]
    above_ma20 = price > ma20
    pool2 = month_up and above_ma20 and s >= 4

    # 🔵 第三池
    pool3 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 5

    # 🔴 第四池
    accel = df["Close"].pct_change().tail(3).mean() > 0
    vol_break = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]
    pool4 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 6 and accel and vol_break

    if pool4:
        return "🔴 第四池"
    elif pool3:
        return "🔵 第三池"
    elif pool2:
        return "🟠 第二池"
    elif pool1:
        return "🟡 第一池"
    else:
        return None


# =========================
# 進出場
# =========================
def trade_levels(price, ma5, ma10, pool):

    if "第四池" in pool:
        stop = ma10
        target = price * 1.25
    elif "第三池" in pool:
        stop = ma5
        target = price * 1.20
    elif "第二池" in pool:
        stop = ma5
        target = price * 1.15
    else:
        stop = ma10
        target = price * 1.10

    return round(price, 2), round(stop, 2), round(target, 2)


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
        except:
            continue

        for t in batch:

            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if t in data.columns.levels[0]:
                        df = data[t]
                    else:
                        continue
                else:
                    df = data

                if df is None or df.empty or len(df) < 30:
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

                s = score(price, ma5, ma10, ma20,
                          df["Volume"].iloc[-1],
                          df["vol_ma5"].iloc[-1],
                          change_pct)

                pool = classify_pool(s, df, price, ma5, ma10, ma20, open_price)

                if pool is None:
                    continue

                entry, stop, target = trade_levels(price, ma5, ma10, pool)

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "池別": pool,
                    "分數": s,
                    "收盤": round(price, 2),
                    "進場": entry,
                    "停損": stop,
                    "目標": target
                })

            except:
                continue

        progress.progress((i + 1) / total_batches)

    df = pd.DataFrame(results)

    if df.empty:
        st.warning("沒有符合條件股票")

    else:

        st.subheader("🔴 第四池")
        st.dataframe(df[df["池別"] == "🔴 第四池"])

        st.subheader("🔵 第三池")
        st.dataframe(df[df["池別"] == "🔵 第三池"])

        st.subheader("🟠 第二池")
        st.dataframe(df[df["池別"] == "🟠 第二池"])

        st.subheader("🟡 第一池")
        st.dataframe(df[df["池別"] == "🟡 第一池"])

        st.session_state["pool1"] = df[df["池別"] == "🟡 第一池"]
        st.session_state["pool2"] = df[df["池別"] == "🟠 第二池"]
        st.session_state["pool3"] = df[df["池別"] == "🔵 第三池"]
        st.session_state["pool4"] = df[df["池別"] == "🔴 第四池"]
