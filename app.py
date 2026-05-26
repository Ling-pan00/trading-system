import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="台股月線負乖離排行",
    layout="wide"
)

st.title("台股月線負乖離排行（高速版）")

st.markdown("篩選條件：股價低於月線 8%（含）以上")

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

            # 避免ETF、權證
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

# 單檔掃描
def scan_stock(stock):

    code = stock["code"]
    name = stock["name"]
    ticker = stock["ticker"]

    try:

        df = yf.download(
            ticker,
            period="3mo",
            interval="1d",
            progress=False,
            auto_adjust=False,
            threads=False
        )

        if df.empty or len(df) < 20:
            return None

        close_series = df["Close"]

        # 避免多欄位
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]

        ma20 = close_series.rolling(20).mean().iloc[-1]
        close = float(close_series.iloc[-1])

        if pd.isna(ma20):
            return None

        bias = ((close - ma20) / ma20) * 100

        if bias <= bias_limit:

            return {
                "股票代號": code,
                "股票名稱": name,
                "收盤價": round(close, 2),
                "月線MA20": round(ma20, 2),
                "乖離率(%)": round(bias, 2)
            }

    except Exception:
        return None

    return None


# 開始篩選
if st.button("開始高速掃描"):

    results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    total = len(stock_list)
    completed = 0

    # 高速多執行緒
    MAX_WORKERS = 20

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        futures = {
            executor.submit(scan_stock, stock): stock
            for stock in stock_list
        }

        for future in as_completed(futures):

            result = future.result()

            if result:
                results.append(result)

            completed += 1

            progress_bar.progress(completed / total)

            if completed % 20 == 0:
                status_text.text(
                    f"已掃描 {completed}/{total}"
                )

    status_text.text("掃描完成")

    if results:

        result_df = pd.DataFrame(results)

        # 負乖離最大排前面
        result_df = result_df.sort_values(
            by="乖離率(%)",
            ascending=True
        )

        st.success(f"找到 {len(result_df)} 檔符合條件股票")

        st.dataframe(
            result_df,
            use_container_width=True,
            height=700
        )

        # 下載CSV
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
