import streamlit as st
import pandas as pd
import yfinance as yf
import twstock


st.set_page_config(
    page_title="台股負乖離反轉掃描（高速版）",
    layout="wide"
)

st.title("🏛️ 台股負乖離反轉掃描（高速版）")

st.markdown("""
### 篩選條件
- 股價低於月線 8%（含）以上
- RSI < 30
- 今日收紅
- 今日成交量 > 5日均量
""")


# =========================
# ⚙️ 參數設定
# =========================
bias_limit = st.slider(
    "負乖離 (%)",
    min_value=-20,
    max_value=-1,
    value=-8
)

rsi_limit = st.slider(
    "RSI 上限",
    min_value=10,
    max_value=50,
    value=30
)


# =========================
# 📊 RSI 計算
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
# 📦 股票池
# =========================
@st.cache_data(ttl=86400)
def get_stock_list():

    stocks = []

    for code, info in twstock.codes.items():

        if info.market in ["上市", "上櫃"]:

            # 排除 ETF / 權證 / 特殊商品
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

st.write(f"📦 股票總數：{len(stock_list)}")


# ticker 對照
ticker_map = {
    stock["ticker"]: {
        "code": stock["code"],
        "name": stock["name"]
    }
    for stock in stock_list
}

tickers = list(ticker_map.keys())


# =========================
# 🚀 開始掃描
# =========================
if st.button("🚀 開始超高速掃描"):

    results = []

    progress = st.progress(0)
    status = st.empty()

    batch_size = 200

    total_batches = (
        len(tickers) + batch_size - 1
    ) // batch_size

    for batch_idx in range(total_batches):

        start = batch_idx * batch_size
        end = start + batch_size

        batch_tickers = tickers[start:end]

        status.text(
            f"📥 下載資料中：第 {batch_idx+1}/{total_batches} 批"
        )

        try:

            # 🚀 批次下載
            data = yf.download(
                tickers=batch_tickers,
                period="3mo",
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True
            )

            for ticker in batch_tickers:

                try:

                    stock_data = data[ticker]

                    if stock_data.empty:
                        continue

                    close = stock_data["Close"]
                    volume = stock_data["Volume"]
                    open_price = stock_data["Open"]

                    # 最少資料需求
                    if len(close) < 20:
                        continue

                    # =========================
                    # 📈 月線
                    # =========================
                    ma20 = close.rolling(20).mean().iloc[-1]

                    if pd.isna(ma20):
                        continue

                    latest_close = float(close.iloc[-1])

                    # =========================
                    # 📉 負乖離
                    # =========================
                    bias = (
                        (latest_close - ma20)
                        / ma20
                    ) * 100

                    # =========================
                    # 📊 RSI
                    # =========================
                    rsi = calculate_rsi(close).iloc[-1]

                    if pd.isna(rsi):
                        continue

                    # =========================
                    # 🟢 今日收紅
                    # =========================
                    is_red = (
                        close.iloc[-1]
                        > open_price.iloc[-1]
                    )

                    # =========================
                    # 📦 成交量條件
                    # =========================
                    vol_ma5 = volume.rolling(5).mean().iloc[-1]

                    latest_vol = volume.iloc[-1]

                    volume_ok = latest_vol > vol_ma5

                    # =========================
                    # 🔥 不破前低（反轉強化）
                    # =========================
                    recent_low = close.tail(5).min()

                    not_break_low = (
                        latest_close >= recent_low
                    )

                    # =========================
                    # 🚀 最終條件
                    # =========================
                    if (
                        bias <= bias_limit
                        and rsi < rsi_limit
                        and is_red
                        and volume_ok
                        and not_break_low
                    ):

                        info = ticker_map[ticker]

                        results.append({
                            "股票代號": info["code"],
                            "股票名稱": info["name"],
                            "收盤價": round(latest_close, 2),
                            "月線MA20": round(ma20, 2),
                            "乖離率(%)": round(bias, 2),
                            "RSI": round(rsi, 2),
                            "成交量": int(latest_vol)
                        })

                except Exception:
                    continue

        except Exception:
            continue

        progress.progress(
            (batch_idx + 1) / total_batches
        )

    status.text("✅ 掃描完成")

    # =========================
    # 📊 顯示結果
    # =========================
    if results:

        result_df = pd.DataFrame(results)

        # 依負乖離排序
        result_df = result_df.sort_values(
            by="乖離率(%)",
            ascending=True
        )

        st.success(
            f"🔥 找到 {len(result_df)} 檔符合條件股票"
        )

        st.dataframe(
            result_df,
            use_container_width=True,
            height=700
        )

        # 📥 CSV下載
        csv = result_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="📥 下載CSV",
            data=csv,
            file_name="台股負乖離反轉排行.csv",
            mime="text/csv"
        )

    else:

        st.warning("⚠️ 沒有符合條件股票")
