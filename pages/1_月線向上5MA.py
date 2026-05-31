import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="法人三池 stable v5", layout="wide")
st.title("📊 三池法人進場系統（穩定修正版）")

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
# 池分類（修正版核心）
# =========================
def classify_pool(open_p, close, high, low, ma5, ma10, ma20, volume):

    # ===== volume 安全處理 =====
    try:
        vol_ma5 = volume.rolling(5).mean().iloc[-1]
        vol_ok = volume.iloc[-1] >= vol_ma5 * 0.8
    except:
        vol_ok = True

    # =========================
    # 🔴 第三池（主升段）
    # =========================
    third_pool = (
        ma5 > ma10 > ma20 and
        close > ma20
    )

    # =========================
    # 🟠 第二池（回測買點）
    # =========================
    second_pool = (
        close > ma20 and
        close > ma5 and
        ma5 > ma10
    )

    # =========================
    # 🟡 第一池（試單轉強）
    # =========================
    first_pool = (
        close > ma20 and
        vol_ok
    )

    # =========================
    # 🚨 互斥排序（關鍵）
    # =========================
    if third_pool:
        return "🔴 第三池（主升）"
    elif second_pool:
        return "🟠 第二池（回測）"
    elif first_pool:
        return "🟡 第一池（試單）"

    return None


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
        status.text(f"📥 {i+1}/{total_batches}")

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
                    if df.empty:
                        continue

                    open_p = df["Open"]
                    close = df["Close"]
                    high = df["High"]
                    low = df["Low"]
                    volume = df["Volume"]

                    if len(close) < 20:
                        continue

                    ma5 = close.rolling(5).mean().iloc[-1]
                    ma10 = close.rolling(10).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]

                    price = close.iloc[-1]

                    # ⭐ 月線濾網（保留）
                    if price <= ma20:
                        continue

                    pool = classify_pool(
                        open_p.iloc[-1],
                        price,
                        high.iloc[-1],
                        low.iloc[-1],
                        ma5,
                        ma10,
                        ma20,
                        volume
                    )

                    if pool is None:
                        continue

                    buy = float(price)

                    # 停損 / 目標
                    if "第二池" in pool:
                        stop = round(ma5, 2)
                        target = round(buy * 1.2, 2)

                    elif "第三池" in pool:
                        stop = round(ma10, 2)
                        target = round(buy * 1.25, 2)

                    else:
                        stop = round(buy * 0.95, 2)
                        target = round(buy * 1.15, 2)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "池別": pool,
                        "收盤": buy,
                        "買進": buy,
                        "停損": stop,
                        "目標": target
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i+1)/total_batches)

    status.text("✅ 完成")

    df = pd.DataFrame(results)

    # =========================
    # Top10
    # =========================
    pool1 = df[df["池別"].str.contains("第一")].head(10)
    pool2 = df[df["池別"].str.contains("第二")].head(10)
    pool3 = df[df["池別"].str.contains("第三")].head(10)

    st.subheader("🟡 第一池 Top10")
    st.dataframe(pool1, use_container_width=True)

    st.subheader("🟠 第二池 Top10")
    st.dataframe(pool2, use_container_width=True)

    st.subheader("🔴 第三池 Top10")
    st.dataframe(pool3, use_container_width=True)

    st.session_state["pool1"] = pool1
    st.session_state["pool2"] = pool2
    st.session_state["pool3"] = pool3


# =========================
# 盤中監控（保留）
# =========================
st.subheader("📈 盤中監控")


def run_monitor(df):

    live = []

    for _, row in df.iterrows():

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
        st.dataframe(run_monitor(st.session_state["pool1"]), use_container_width=True)

    with col2:
        st.markdown("### 🟠 第二池")
        st.dataframe(run_monitor(st.session_state["pool2"]), use_container_width=True)

    with col3:
        st.markdown("### 🔴 第三池")
        st.dataframe(run_monitor(st.session_state["pool3"]), use_container_width=True)
