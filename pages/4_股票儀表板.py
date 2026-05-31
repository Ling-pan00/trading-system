import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="三池選股系統（乾淨版）", layout="wide")

st.title("📊 三池選股系統（純策略版）")

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

    # 🟡 動能股池
    if (
        change_pct > 3 and change_pct < 10
        and close > ma5
        and vol > vol_ma5
    ):
        return "動能股"

    # 🚀 突破股池
    if (
        close > ma20
        and vol > vol_ma5
        and is_red
        and close > ma10
    ):
        return "突破股"

    # 🧊 回檔強勢股池
    if (
        close < ma5
        and close > ma10
        and close > ma20
    ):
        return "回檔股"

    return None


# =========================
# 風控濾網
# =========================
def trade_filter(change_pct, volume_ok, upper_shadow):

    # ❌ +8% 不追
    no_fomo = change_pct < 8

    # ❌ 連3紅K（簡化：略過但保守）
    no_overheat = True

    # ❌ 爆量長上影
    no_distribution = not upper_shadow

    return no_fomo and no_overheat and no_distribution


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

        status.text(f"📥 第 {i+1}/{total_batches} 批")

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

                    volume_ok = latest_vol > vol_ma5

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

                    ok = trade_filter(change_pct, volume_ok, upper_shadow)

                    if pool and ok:

                        info = ticker_map[t]

                        results.append({
                            "代號": info["code"],
                            "名稱": info["name"],
                            "收盤": round(latest_close, 2),
                            "漲跌%": round(change_pct, 2),
                            "量": int(latest_vol),
                            "池別": pool
                        })

                except:
                    continue

        except:
            continue

        progress.progress((i + 1) / total_batches)

    status.text("✅ 完成")

    # =========================
    # 輸出
    # =========================
    if results:

        df = pd.DataFrame(results)

        # 池別統計
        pool_count = df["池別"].value_counts()

        # 主交易池
        main_pool = pool_count.idxmax() if len(pool_count) > 0 else "無"

        st.subheader("📌 今日主交易池")
        st.write(main_pool)

        st.subheader("🥇 Top 10 強勢股")
        st.dataframe(df.head(10), use_container_width=True)

        st.subheader("📊 三池分布")
        st.write(pool_count)

    else:
        st.warning("⚠️ 今天沒有符合條件的股票")
