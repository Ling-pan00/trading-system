import requests


def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i["Code"]
        name = i.get("Name", "")

        # ✔ 必須是股票代碼
        if not code.isdigit() or len(code) != 4:
            continue

        # 🚨 ETF / ETN 關鍵排除（核心）
        if "ETF" in name.upper():
            continue

        if "指數" in name:
            continue

        if "槓桿" in name:
            continue

        if "反向" in name:
            continue

        if "債券" in name:
            continue

        stocks.append(code + ".TW")

    return stocks
