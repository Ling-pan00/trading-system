# app.py

```python
import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="三池獨立監控系統", layout="wide")

st.title("📊 三池獨立交易監控系統 Pro")

# =========================
# 股票清單
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

ticker_map = {
    s["ticker"]: s
    for s in stock_list
}

tickers = list(ticker_map.keys())

st.write(f"📦 股票數量：{len(tickers)}")


# =========================
# 三池策略
# =========================
def classify_pool(df):

    try:

        close = df["Close"]
        volume = df["Volume"]
        open_ = df["Open"]
        high = df["High"]
        low = df["Low"]

        if len(close) < 30:
            return None

        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()

        ma20_up = (
            ma20.iloc[-1]
            >
            ma20.iloc[-2]
        )

        # =====================
        # 第一池
        # =====================

        broke = (
            (close < ma5)
            .tail(10)
            .any()
        )

        first_rebound = (
            close.iloc[-1]
            >
            ma5.iloc[-1]
        )

        vol_ok = (
            volume.iloc[-1]
            >=
            volume.iloc[-2] * 0.8
        )

        body = abs(
            close.iloc[-1]
            -
            open_.iloc[-1]
        )

        upper_shadow = (
            high.iloc[-1]
            -
            max(
                open_.iloc[-1],
                close.iloc[-1]
            )
        )

        shadow_ok = (
            upper_shadow <= body * 1.5
        )

        pool1 = (
            ma20_up
            and broke
            and first_rebound
            and vol_ok
            and shadow_ok
        )

        # =====================
        # 第二池
        # =====================

        pool2 = (

            ma20_up

            and

            close.iloc[-1]
            >
            ma5.iloc[-1]

            and

            low.iloc[-1]
            <=
            ma5.iloc[-1] * 1.01

            and

            volume.iloc[-1]
            >=
            volume.iloc[-2] * 0.8
        )

        # =====================
        # 第三池
        # =====================

        vol_ma20 = (
            volume
            .rolling(20)
            .mean()
        )

        body_pct = (
            (
                close.iloc[-1]
                -
                open_.iloc[-1]
            )
            /
            open_.iloc[-1]
        )

        volume_ratio = (
            volume.iloc[-1]
            /
            max(
                vol_ma20.iloc[-1],
                1
            )
        )

        not_exhaust = not (
            body_pct > 0.07
            and
            volume_ratio > 2
        )

        pool3 = (

            ma20_up

            and

            close.iloc[-1]
            >
            ma20.iloc[-1]

            and

            ma5.iloc[-1]
            >
            ma10.iloc[-1]
            >
            ma20.iloc[-1]

            and

            close.iloc[-1]
            >
            ma10.iloc[-1]

            and

            not_exhaust
        )

        if pool3:
            return "🔴 第三池"

        elif pool2:
            return "🟠 第二池"

        elif pool1:
            return "🟡 第一池"

        return None

    except:
        return None


# =========================
# 盤中訊號
# =========================
def intraday_signal(
    open_p,
    close_y,
    low_y,
    high_y,
    vol,
    vol_y
):

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
# 盤後選股
# =========================
if st.button("🚀 盤後選股"):

    results = []

    batch_size = 200

    total_batches = (
        len(tickers)
        + batch_size
        - 1
    ) // batch_size

    progress = st.progress(0)

    status = st.empty()

    for i in range(total_batches):

        batch = tickers[
            i*batch_size:(i+1)*batch_size
        ]

        status.text(
            f"📥 {i+1}/{total_batches}"
        )

        try:

            data = yf.download(
                tickers=batch,
                period="3mo",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=True,
                auto_adjust=False
            )

            for t in batch:

                try:

                    df_s = data[t]

                    if df_s.empty:
                        continue

                    close = df_s["Close"]

                    low = df_s["Low"]

                    if len(close) < 30:
                        continue

                    pool = classify_pool(df_s)

                    if pool is None:
                        continue

                    ma5 = (
                        close
                        .rolling(5)
                        .mean()
                        .iloc[-1]
                    )

                    ma10 = (
                        close
                        .rolling(10)
                        .mean()
                        .iloc[-1]
                    )

                    buy = float(
                        close.iloc[-1]
                    )

                    if pool == "🟡 第一池":

                        stop = float(
                            low.iloc[-1]
                        )

                        target = round(
                            buy * 1.15,
                            2
                        )

                    elif pool == "🟠 第二池":

                        stop = round(
                            ma5,
                            2
                        )

                        target = round(
                            buy * 1.20,
                            2
                        )

                    else:

                        stop = round(
                            ma10,
                            2
                        )

                        target = round(
                            buy * 1.25,
                            2
                        )

                    results.append({

                        "代號":
                        ticker_map[t]["code"],

                        "名稱":
                        ticker_map[t]["name"],

                        "ticker":
                        t,

                        "池別":
                        pool,

                        "收盤":
                        round(buy, 2),

                        "買進價":
                        round(buy, 2),

                        "停損價":
                        stop,

                        "目標價":
                        target

                    })

                except:
                    continue

        except:
            continue

        progress.progress(
            (i+1)/total_batches
        )

    status.text("✅ 完成")

    df = pd.DataFrame(results)

    pool1_df = (
        df[df["池別"] == "🟡 第一池"]
        .head(10)
    )

    pool2_df = (
        df[df["池別"] == "🟠 第二池"]
        .head(10)
    )

    pool3_df = (
        df[df["池別"] == "🔴 第三池"]
        .head(10)
    )

    st.session_state["pool1"] = pool1_df
    st.session_state["pool2"] = pool2_df
    st.session_state["pool3"] = pool3_df

    st.subheader("🟡 第一池 Top10")
    st.dataframe(
        pool1_df,
        use_container_width=True
    )

    st.subheader("🟠 第二池 Top10")
    st.dataframe(
        pool2_df,
        use_container_width=True
    )

    st.subheader("🔴 第三池 Top10")
    st.dataframe(
        pool3_df,
        use_container_width=True
    )


# =========================
# 盤中監控
# =========================
st.subheader("📈 盤中三池監控")


def run_monitor(df):

    live = []

    for _, row in df.iterrows():

        try:

            t = row["ticker"]

            data = yf.download(
                t,
                period="5d",
                interval="1d",
                progress=False
            )

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

            vol_y = (
                volume
                .rolling(5)
                .mean()
                .iloc[-1]
            )

            sig = intraday_signal(
                open_now,
                close_y,
                low_y,
                high_y,
                vol,
                vol_y
            )

            live.append({

                "代號":
                row["代號"],

                "名稱":
                row["名稱"],

                "池別":
                row["池別"],

                "訊號":
                sig

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

        st.markdown(
            "### 🟡 第一池"
        )

        st.dataframe(
            run_monitor(
                st.session_state["pool1"]
            ),
            use_container_width=True
        )

    with col2:

        st.markdown(
            "### 🟠 第二池"
        )

        st.dataframe(
            run_monitor(
                st.session_state["pool2"]
            ),
            use_container_width=True
        )

    with col3:

        st.markdown(
            "### 🔴 第三池"
        )

        st.dataframe(
            run_monitor(
                st.session_state["pool3"]
            ),
            use_container_width=True
        )
```
