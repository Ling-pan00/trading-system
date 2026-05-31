import streamlit as st
import pandas as pd
import requests
import yfinance as yf
from multiprocessing import Pool, cpu_count

st.title("🚀 2000檔台股加速選股（單檔版）")

# =========================
# 股票池（TWSE + OTC）
# =========================
@st.cache_data
def get_universe():

    try:
        twse = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            timeout=10
        ).json()
        twse = [x["Code"] + ".TW" for x in twse]
    except:
        twse = []

    try:
        tpex = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_stk_info",
            timeout=10
        ).json()
        tpex = [x["SecuritiesCompanyCode"] + ".TWO" for x in tpex]
    except:
        tpex = []

    return list(set(twse + tpex))


# =========================
# 單股抓取
# =========================
def fetch(ticker):

    try:
        df = yf.download(ticker, period="2mo", interval="1d", progress=False)

        if len(df) < 20:
            return None

        close = df["Close"].iloc[-1]
        prev = df["Close"].iloc[-2]

        volume = df["Volume"].iloc[-1]
        avg_volume = df["Volume"].rolling(5).mean().iloc[-1]

        ma5 = df["Close"].rolling(5).mean().iloc[-1]
        ma20 = df["Close"].rolling(20).mean().iloc[-1]

        return {
            "ticker": ticker,
            "close": float(close),
            "change_pct": float((close - prev) / prev * 100),
            "volume": float(volume),
            "avg_volume": float(avg_volume),
            "ma5": float(ma5),
            "ma20": float(ma20),
        }

    except:
        return None


# =========================
# 打分
# =========================
def score(x):

    s = 0

    if x["change_pct"] > 3:
        s += 1
    if x["volume"] > x["avg_volume"]:
        s += 1
    if x["close"] > x["ma5"]:
        s += 1
    if x["ma5"] > x["ma20"]:
        s += 1
    if x["change_pct"] >= 8:
        s -= 2

    return s


# =========================
# 平行掃描
# =========================
def scan(tickers):

    with Pool(cpu_count()) as p:
        res = p.map(fetch, tickers)

    res = [r for r in res if r is not None]

    for r in res:
        r["score"] = score(r)

    return pd.DataFrame(res)


# =========================
# 主流程
# =========================
tickers = get_universe()

st.write("📊 股票數量：", len(tickers))

df = scan(tickers)

df = df.sort_values("score", ascending=False)

# 市場狀態
ratio = len(df[df["score"] >= 3]) / len(df)

if ratio > 0.4:
    mode = "🔥 強勢盤"
elif ratio > 0.2:
    mode = "🟢 正常盤"
else:
    mode = "🟡 偏弱盤"

st.subheader("📌 市場狀態")
st.write(mode)

st.subheader("🥇 Top 10")
st.dataframe(df.head(10))

st.subheader("📊 全市場")
st.dataframe(df)
