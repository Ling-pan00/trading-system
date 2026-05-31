import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np

st.set_page_config(page_title="三池量化 Pro v2.1", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.1（完整穩定版）")


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
# 四池分類（核心）
# =========================
def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 25:
        return None

    ma20_series = df["ma20"].dropna()
    if len(ma20_series) < 10:
        return None

    # =========================
    # 趨勢基礎
    # =========================
    month_up = ma20_series.iloc[-1] > ma20_series.iloc[-3]
    above_ma20 = price > ma20

    # =========================
    # 🟡 第一池：洗盤轉強
    # =========================
    dipped = (df["Close"] < df["ma5"]).any()

    reclaim_ma5 = (
        df["Close"].iloc[-2] < df["ma5"].iloc[-2] and
        price > ma5
    )

    red_k = price > open_price

    pool1 = month_up and above_ma20 and dipped and reclaim_ma5 and red_k


    # =========================
    # 🟠 第二池：趨勢初期
    # =========================
    pool2 = month_up and above_ma20 and s >= 4


    # =========================
    # 🔵 第三池：均線多頭
    # =========================
    pool3 = month_up and above_ma20 and ma5 > ma10 > ma20 and s >= 5


    # =========================
    # 🔴 第四池：主升段
    # =========================
    accel = df["Close"].pct_change().tail(3).mean() > 0
    vol_break = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

    pool4 = (
        month_up and above_ma20 and
        ma5 > ma10 > ma20 and
        s >= 6 and
        accel and
        vol_break
    )


    # =========================
    # 優先順序
    # =========================
    if pool4:
        return "🔴 第四池（主升段）"
    elif pool3:
        return "🔵 第三池（趨勢成形）"
    elif pool2:
        return "🟠 第二池（趨勢初期）"
    elif pool1:
        return "🟡 第一池（洗盤轉強）"
    else:
        return None


# =========================
# 進出場模型
# =========================
def trade_levels(price, ma5, ma10, pool):

    entry = price

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

                    change_pct = (
                        df["Close"].iloc[-1] - df["Close"].iloc[-2]
                    ) / df["Close"].iloc[-2]

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
                        "池別": pool,
                        "分數": s,
                        "收盤": round(price, 2),
                        "進場": entry,
                        "停損": stop,
                        "目標": target
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

        st.subheader("🔴 第四池（主升段）")
        st.dataframe(df[df["池別"].str.contains("第四池")].head(20))

        st.subheader("🔵 第三池（趨勢成形）")
        st.dataframe(df[df["池別"].str.contains("第三池")].head(20))

        st.subheader("🟠 第二池（趨勢初期）")
        st.dataframe(df[df["池別"].str.contains("第二池")].head(20))

        st.subheader("🟡 第一池（洗盤轉強）")
        st.dataframe(df[df["池別"].str.contains("第一池")].head(20))
