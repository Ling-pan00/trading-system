import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="三池選股系統 v2", layout="wide")

st.title("📊 三池選股系統（分池 + 評分版）")

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

ticker_map = {
    s["ticker"]: {"code": s["code"], "name": s["name"]}
    for s in stock_list
}

tickers = list(ticker_map.keys())

st.write(f"📦 股票數量：{len(tickers)}")


# =========================
# 三池分類
# =========================
def classify_pool(change_pct, close, ma5, ma10, ma20, vol, vol_ma5, is_red):

    # 🟡 動能股
    if (
        change_pct > 3 and change_pct < 10
        and close > ma5
        and vol > vol_ma5
    ):
        return "動能股"

    # 🚀 突破股
    if (
        close > ma20
        and vol > vol_ma5
        and is_red
        and close > ma10
    ):
        return "突破股"

    # 🧊 回檔股
    if (
        close < ma5
        and close > ma10
        and close > ma20
    ):
        return "回檔股"

    return None


# =========================
# 評分系統
# =========================
def score(change_pct, close, ma5, ma10, ma20, vol, vol_ma5):

    s = 0

    if close > ma5:
        s += 1

    if ma5 > ma10:
        s += 1

    if ma10 > ma20:
        s += 1

    if vol > vol_ma5:
        s += 1

    if change_pct > 3:
        s += 1

    return s


# =========================
# 掃描開始
# =========================
if st.button("🚀 開始掃描"):

    results = []

    progress = st.progress(0)
    status = st.empty()

    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    for i in range(total_batches):

        batch = tickers[i*batch_size:(i+1)*batch_size]

        status.text(f"📥 批次 {i+1}/{total_batches}")

        try:
            data = yf.download(
                tickers=batch,
                period="3mo",
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False
            )

            for t in batch:

                try:
                    stock = data[t]
                    if stock.empty:
                        continue

                    close = stock["Close"]
                    open_price = stock["Open"]
                    volume = stock["Volume"]
                    high = stock["High"]

                    if len(close) < 20:
                        continue

                    latest_close = float(close.iloc[-1])
                    latest_vol = float(volume.iloc[-1])

                    ma5 = close.rolling(5).mean().iloc[-1]
                    ma10 = close.rolling(10).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]

                    vol_ma5 = volume.rolling(5).mean().iloc[-1]

                    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

                    is_red = latest_close > open_price.iloc[-1]

                    upper_shadow = (
                        high.iloc[-1] - latest_close
                    ) > (latest_close - open_price.iloc[-1])

                    pool = classify_pool(
                        change_pct,
                        latest_close,
                        ma5,
                        ma10,
                        ma20,
                        latest_vol,
                        vol_ma5,
                        is_red
                    )

                    s = score(
                        change_pct,
                        latest_close,
                        ma5,
                        ma10,
                        ma20,
                        latest_vol,
                        vol_ma5
                    )

                    # 風控：+8%不追 + 長上影排除
                    ok = (
                        change_pct < 8
                        and not upper_shadow
                    )

                    if pool and ok:

                        info = ticker_map[t]

                        results.append({
                            "代號": info["code"],
                            "名稱": info["name"],
                            "收盤": round(latest_close, 2),
                            "漲跌%": round(change_pct, 2),
                            "量": int(latest_vol),
                            "池別": pool,
                            "分數": s
                        })

                except:
                    continue

        except:
            continue

        progress.progress((i + 1) / total_batches)

    status.text("✅ 完成")

    # =========================
    # 結果處理
    # =========================
    if results:

        df = pd.DataFrame(results)

        df = df.sort_values("分數", ascending=False)

        # =========================
        # 三池分開 Top 5
        # =========================
        momentum_df = df[df["池別"] == "動能股"].head(5)
        breakout_df = df[df["池別"] == "突破股"].head(5)
        pullback_df = df[df["池別"] == "回檔股"].head(5)

        # =========================
        # 主交易池
        # =========================
        pool_count = df["池別"].value_counts()
        main_pool = pool_count.idxmax() if len(pool_count) > 0 else "無"

        # =========================
        # UI
        # =========================
        st.subheader("📌 今日主交易池")
        st.write(main_pool)

        st.subheader("🟡 動能股 Top 5")
        st.dataframe(momentum_df, use_container_width=True)

        st.subheader("🚀 突破股 Top 5")
        st.dataframe(breakout_df, use_container_width=True)

        st.subheader("🧊 回檔股 Top 5")
        st.dataframe(pullback_df, use_container_width=True)

        st.subheader("🥇 今日總強勢 Top 10")
        st.dataframe(df.head(10), use_container_width=True)

        st.subheader("📊 三池分布")
        st.write(pool_count)

    else:
        st.warning("⚠️ 沒有符合條件的股票")
