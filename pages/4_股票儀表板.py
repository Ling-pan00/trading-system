import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(
    page_title="三池選股系統",
    layout="wide"
)

st.title("📊 三池 + 自動打分選股系統")

# =========================
# ⚙️ 參數
# =========================
bias_limit = st.slider("負乖離 (%)", -20, -1, -8)
rsi_limit = st.slider("RSI 上限", 10, 50, 30)

# =========================
# RSI
# =========================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

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
def classify_pool(bias, rsi, close, ma5, ma20, volume_ok):

    # 動能股
    if close > ma5 and volume_ok and rsi > 45:
        return "動能股"

    # 突破股
    if close > ma20 and volume_ok:
        return "突破股"

    # 回檔股
    if close < ma5 and close > ma20:
        return "回檔股"

    return None

# =========================
# 打分系統
# =========================
def score_pool(bias, rsi, close, ma5, ma20, volume_ok):

    score = 0

    if close > ma5:
        score += 2

    if ma5 > ma20:
        score += 2

    if volume_ok:
        score += 1

    if rsi > 40 and rsi < 70:
        score += 1

    # 不追高
    if bias > 8:
        score -= 3

    return score

# =========================
# 掃描
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
                    volume = stock["Volume"]
                    open_price = stock["Open"]

                    if len(close) < 20:
                        continue

                    ma5 = close.rolling(5).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]

                    latest = float(close.iloc[-1])
                    latest_vol = float(volume.iloc[-1])

                    # RSI
                    rsi = calculate_rsi(close).iloc[-1]
                    if pd.isna(rsi):
                        continue

                    # 負乖離
                    bias = (latest - ma20) / ma20 * 100

                    # 成交量
                    vol_ma5 = volume.rolling(5).mean().iloc[-1]
                    volume_ok = latest_vol > vol_ma5

                    # 紅K
                    is_red = latest > open_price.iloc[-1]

                    # 不破低
                    not_break_low = latest >= close.tail(5).min()

                    pool = classify_pool(
                        bias, rsi, latest, ma5, ma20, volume_ok
                    )

                    score = score_pool(
                        bias, rsi, latest, ma5, ma20, volume_ok
                    )

                    if pool and is_red and volume_ok and not_break_low:

                        info = ticker_map[t]

                        results.append({
                            "代號": info["code"],
                            "名稱": info["name"],
                            "收盤": round(latest, 2),
                            "乖離": round(bias, 2),
                            "RSI": round(rsi, 2),
                            "量": int(latest_vol),
                            "池別": pool,
                            "分數": score
                        })

                except:
                    continue

        except:
            continue

        progress.progress((i+1)/total_batches)

    status.text("✅ 完成")

    # =========================
    # 結果
    # =========================
    if results:

        df = pd.DataFrame(results)

        df = df.sort_values("分數", ascending=False)

        # 今日主池
        pool_count = df["池別"].value_counts()

        if len(pool_count) > 0:
            main_pool = pool_count.idxmax()
        else:
            main_pool = "無明確主力"

        st.subheader("📌 今日主交易池")
        st.write(main_pool)

        st.subheader("🥇 Top 10")
        st.dataframe(df.head(10), use_container_width=True)

        st.subheader("📊 三池分布")
        st.write(pool_count)

    else:
        st.warning("沒有符合條件的股票")
