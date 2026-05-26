import requests


def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i["Code"]

        # 必須是 4 位數
        if not code.isdigit() or len(code) != 4:
            continue

        # 🚨 ETF 關鍵排除（核心修正）
        if code.startswith("00"):
            continue

        stocks.append(code + ".TW")

    return stocks
