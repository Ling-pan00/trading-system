import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="三池交易看板 Pro", layout="wide")

st.title("📊 三池交易看板（完整版本）")

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

st.write(f"📦 股票數量：{len(tickers)}")


# =========================
# 評分系統
# =========================
def score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):

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

    return s


# =========================
# 三池分類（核心恢復）
# =========================
def classify_pool(s):

    if s >= 5:
        return "🚀 突破股"
    elif s >= 3:
        return "🟡 動能股"
    else:
        return "🧊 回檔股"


# =========================
# 盤中訊號
# =========================
def intraday_signal(open_p, close_y, low_y, high_y, vol, vol_y):

    strong = open_p >= close_y
    hold = open_p >= low_y
    vol_ok = vol >= vol_y * 0.7
    breakout = open_p > high_y

    if strong and hold and vol_ok:
        if breakout:
            return "🟢 BUY（追強）"
        return "🟢 BUY（回測）"

    if hold:
        return "🟡 WATCH"

    return "🔴 NO"


# =========================
# 盤後掃描
# =========================
if st.button("🚀 盤後選股"):

    results = []

    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    progress = st.progress(0)
    status = st.empty()

    for i in range(total_batches):

        batch = tickers[i*batch_size:(i+1)*batch_size]

        status.text(f"📥 批次 {i+1}/{total_batches}")

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
                    df_s = data[t]
                    if df_s.empty:
                        continue

                    close = df_s["Close"]
                    volume = df_s["Volume"]

                    if len(close) < 20:
                        continue

                    ma5 = close.rolling(5).mean().iloc[-1]
                    ma10 = close.rolling(10).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]

                    vol_ma5 = volume.rolling(5).mean().iloc[-1]

                    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

                    s = score(
                        close.iloc[-1],
                        ma5,
                        ma10,
                        ma20,
                        volume.iloc[-1],
                        vol_ma5,
                        change_pct
                    )

                    pool = classify_pool(s)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "分數": s,
                        "池別": pool,
                        "收盤": float(close.iloc[-1])
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i+1)/total_batches)

    status.text("✅ 完成")

    df = pd.DataFrame(results)

    # =========================
    # 三池 Top5（核心恢復）
    # =========================
    breakout = df[df["池別"] == "🚀 突破股"].sort_values("分數", ascending=False).head(5)
    momentum = df[df["池別"] == "🟡 動能股"].sort_values("分數", ascending=False).head(5)
    pullback = df[df["池別"] == "🧊 回檔股"].sort_values("分數", ascending=False).head(5)

    # =========================
    # 合併候選（5~10檔）
    # =========================
    candidates = pd.concat([breakout, momentum, pullback]).sort_values("分數", ascending=False).head(10)

    st.subheader("🚀 突破股 Top 5")
    st.dataframe(breakout, use_container_width=True)

    st.subheader("🟡 動能股 Top 5")
    st.dataframe(momentum, use_container_width=True)

    st.subheader("🧊 回檔股 Top 5")
    st.dataframe(pullback, use_container_width=True)

    st.subheader("📦 合併候選（5~10檔）")
    st.dataframe(candidates, use_container_width=True)

    st.session_state["candidates"] = candidates


# =========================
# 盤中監控（不變）
# =========================
st.subheader("📈 盤中監控")

if st.button("🔄 更新盤中訊號"):

    if "candidates" not in st.session_state:
        st.warning("請先盤後選股")
        st.stop()

    candidates = st.session_state["candidates"]

    live = []

    for _, row in candidates.iterrows():

        try:
            t = row["ticker"]

            data = yf.download(t, period="5d", interval="1d", progress=False)

            close = data["Close"]
            volume = data["Volume"]
            open_p = data["Open"]
            high = data["High"]
            low = data["Low"]

            open_now = open_p.iloc[-1]
            close_y = close.iloc[-2]
            low_y = low.min()
            high_y = high.max()

            vol = volume.iloc[-1]
            vol_y = volume.rolling(5).mean().iloc[-1]

            sig = intraday_signal(
                open_now,
                close_y,
                low_y,
                high_y,
                vol,
                vol_y
            )

            live.append({
                "代號": row["代號"],
                "名稱": row["名稱"],
                "池別": row["池別"],
                "分數": row["分數"],
                "訊號": sig
            })

        except:
            continue

    st.dataframe(pd.DataFrame(live), use_container_width=True)
