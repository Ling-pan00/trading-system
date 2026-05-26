import requests
import pandas as pd


# =========================
# 📊 取得全市場股票
# =========================
def get_raw_stock_list():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i.get("Code", "")
        name = i.get("Name", "")

        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        # 🚨 排除 ETF / ETN
        if any(x in str(name) for x in ["ETF", "ETN", "指數", "槓桿", "反向", "債券"]):
            continue

        # 🚨 再保護一次
        if code.startswith(("00", "006", "008", "009")):
            continue

        stocks.append(code)

    return stocks


# =========================
# 🧠 動態流動性股票池（核心）
# =========================
def build_universe(top_n=300):

    raw = get_raw_stock_list()

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    df = pd.DataFrame(data)

    # 只留合法股票
    df = df[df["Code"].str.isdigit()]
    df = df[df["Code"].str.len() == 4]

    # 排 ETF / ETN
    df = df[~df["Name"].str.contains("ETF|ETN|指數|槓桿|反向|債券", na=False)]

    # 轉數字
    df["TradeVolume"] = pd.to_numeric(df["TradeVolume"], errors="coerce")
    df["TradeValue"] = pd.to_numeric(df["TradeValue"], errors="coerce")

    # 🚀 流動性評分（核心）
    df["LiquidityScore"] = (
        df["TradeVolume
