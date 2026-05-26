import requests
import pandas as pd
import yfinance as yf


# =========================
# 📊 取得台股全市場
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return [i["Code"] for i in data if i["Code"].isdigit()]


# =========================
# 🟢 Tier 1：法人核心池
# =========================
def tier1(stocks):

    result = []

    for s in stocks:

        try:
            df = yf.download(f"{s}.TW", period="1mo", progress=False)

            if df is None or df.empty:
                continue

            vol = df["Volume"].mean()
            price = df["Close"].iloc[-1]

            if vol > 1_000_000 and price > 30:
                result.append(s)

        except:
            continue

    return result


# =========================
# 🟡 Tier 2：成長動能股
# =========================
def tier2(stocks):

    result = []

    for s in stocks:

        try:
            df = yf.download(f"{s}.TW", period="3mo", progress=False)

            if df is None or df.empty:
                continue

            ret = df["Close"].pct_change().mean()
            vol = df["Volume"].mean()

            if ret > 0 and vol > 300000:
                result.append(s)

        except:
            continue

    return result


# =========================
# 🔵 Tier 3：防守穩定股
# =========================
def tier3(stocks):

    result = []

    for s in stocks:

        try:
            df = yf.download(f"{s}.TW", period="3mo", progress=False)

            if df is None or df.empty:
                continue

            returns = df["Close"].pct_change().dropna()
            volatility = returns.std()

            if volatility < 0.015:
                result.append(s)

        except:
            continue

    return result


# =========================
# 🏛️ 三層股票池主函數
# =========================
def build_three_tier_universe():

    stocks = get_universe()

    t1 = tier1(stocks)
    t2 = tier2(stocks)
    t3 = tier3(stocks)

    return {
        "Tier 1（核心法人）": [f"{s}.TW" for s in t1],
        "Tier 2（成長動能）": [f"{s}.TW" for s in t2],
        "Tier 3（防守穩定）": [f"{s}.TW" for s in t3],
    }
