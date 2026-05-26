import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(
    page_title="台股月線負乖離排行（超高速版）",
    layout="wide"
)

st.title("台股月線負乖離排行（超高速版）")

st.markdown("條件：股價低於月線 8%（含）以上")

# 負乖離設定
bias_limit = st.slider(
    "負乖離 (%)",
    min_value=-20,
    max_value=-1,
    value=-8
)

# 股票池
@st.cache_data(ttl=86400)
def get_stock_list():

    stocks = []

    for code, info in twstock.codes.items():

        if info.market in ["上市", "上櫃"]:

            # 排除ETF、權證
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

st.write(f"股票總數：{len(stock_list)}")

# 建立 ticker 對照
ticker_map = {
    stock["ticker"]: {
        "code": stock["code"],
        "name": stock["name"]
    }
    for stock in stock_list
}

tickers = list(ticker_map.keys())

# 開始掃描
if st.button("開始超高速掃描"):

    results = []

    progress = st.progress(0)
    status = st.empty()

    # 每批抓幾檔
    batch_size = 200

    total_batches = (
        len(tickers) + batch_size - 1
    ) // batch_size

    for batch_idx in range(total_batches):

        start = batch_idx * batch_size
        end = start + batch_size

        batch_tickers = tickers[start:end]

        status.text(
            f"下載資料中：第 {batch_idx+1}/{total_batches} 批"
        )

        try:

            # 一次下載整批
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

                    # 個股資料
                    stock_data = data[ticker]

                    if stock_data.empty:
                        continue

                    close = stock_data["Close"]

                    if len(close) < 20:
                        continue

                    ma20 = close.rolling(20).mean().iloc[-1]

                    latest_close = float(close.iloc[-1])

                    if pd.isna(ma20):
                        continue

                    # 乖離率
                    bias = (
                        (latest_close - ma20)
                        / ma20
                    ) * 100

                    # 篩選
                    if bias <= bias_limit:

                        info = ticker_map[ticker]

                        results.append({
                            "股票代號": info["code"],
                            "股票名稱": info["name"],
                            "收盤價": round(latest_close, 2),
                            "月線MA20": round(ma20, 2),
                            "乖離率(%)": round(bias, 2)
                        })

                except Exception:
                    continue

        except Exception:
            continue

        progress.progress(
            (batch_idx + 1) / total_batches
        )

    status.text("掃描完成")

    # 顯示結果
    if results:

        result_df = pd.DataFrame(results)

        # 排序
        result_df = result_df.sort_values(
            by="乖離率(%)",
            ascending=True
        )

        st.success(
            f"找到 {len(result_df)} 檔符合條件股票"
        )

        st.dataframe(
            result_df,
            use_container_width=True,
            height=700
        )

        # CSV下載
        csv = result_df.to_csv(
            index=False
        ).encode("utf-8-sig")

        st.download_button(
            label="下載CSV",
            data=csv,
            file_name="台股月線負乖離排行.csv",
            mime="text/csv"
        )

    else:

        st.warning("沒有符合條件股票")
