import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="交易監控系統 Pro", layout="wide")

st.title("📊 盤後 + 盤中交易監控系統")

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
# 評分系統
# =========================
def score(change_pct, close, ma5, ma10, ma20, vol, vol_ma5):

    s = 0

    if close > ma5:
        s += 2
    if ma5 > ma10:
        s += 1
    if ma10 > ma20:
        s += 1
    if vol > vol_ma5:
        s += 2
    if change_pct > 0:
        s += 1
    if change_pct < -3:
        s -= 2

    return s


# =========================
# 三池分類
# =========================
def classify_pool(score):

    if score >= 5:
        return "🚀 強勢突破"
    elif score >= 3:
        return "🟡 動能中段"
    else:
        return "🧊 回檔低檔"


# =========================
# 盤中交易訊號
# =========================
def intraday_signal(open_p, high_y, low_y, close_y, vol, vol_y):

    strong_open = open_p >= close_y
    hold_low = open_p >= low_y
    vol_ok = vol >= vol_y * 0.7
    breakout = open_p > high_y

    if strong_open and hold_low and vol_ok:
        if breakout:
            return "🟢 BUY（追強）"
        else:
            return "🟢 BUY（回測）"

    if hold_low:
        return "🟡 WATCH"

    return "🔴 NO"


# =========================
# 掃描（盤後）
# =========================
if st.button("🚀 盤後掃描"):

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
                    ma10 = close.rolling(10).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]

                    vol_ma5 = volume.rolling(5).mean().iloc[-1]

                    latest_close = float(close.iloc[-1])
                    latest_vol = float(volume.iloc[-1])

                    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

                    s = score(
                        change_pct,
                        latest_close,
                        ma5,
                        ma10,
                        ma20,
                        latest_vol,
                        vol_ma5
                    )

                    pool = classify_pool(s)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "收盤": round(latest_close, 2),
                        "漲跌%": round(change_pct, 2),
                        "量": int(latest_vol),
                        "分數": s,
                        "池別": pool
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i + 1) / total_batches)

    status.text("✅ 盤後完成")

    df = pd.DataFrame(results)
    df = df.sort_values("分數", ascending=False)

    candidates = df.head(10)

    st.subheader("📦 盤後候選股 Top 10")
    st.dataframe(candidates, use_container_width=True)


    # =========================
    # 盤中監控
    # =========================
    st.subheader("📈 盤中監控")

    if st.button("🔄 更新盤中訊號"):

        live_results = []

        for _, row in candidates.iterrows():

            try:
                t = row["ticker"]
                data = yf.download(t, period="5d", interval="1d", progress=False)

                close = data["Close"]
                volume = data["Volume"]
                open_price = data["Open"]
                high = data["High"]
                low = data["Low"]

                open_p = open_price.iloc[-1]
                close_y = close.iloc[-2]
                low_y = low.min()
                high_y = high.max()
                vol = volume.iloc[-1]
                vol_y = volume.rolling(5).mean().iloc[-1]

                signal = intraday_signal(
                    open_p,
                    high_y,
                    low_y,
                    close_y,
                    vol,
                    vol_y
                )

                live_results.append({
                    "代號": row["代號"],
                    "名稱": row["名稱"],
                    "池別": row["池別"],
                    "分數": row["分數"],
                    "訊號": signal
                })

            except:
                continue

        st.dataframe(pd.DataFrame(live_results), use_container_width=True)
