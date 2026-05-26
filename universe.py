import requests


# =========================
# 📊 取得台股全市場
# =========================
def get_raw_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return [i["Code"] for i in data if i["Code"].isdigit()]


# =========================
# 🧠 穩定股票池（法人平衡版）
# =========================
def build_universe(limit=60):

    raw = get_raw_universe()

    stocks = []

    for code in raw:

        # ✔ 只保留 4 位數股票
        if len(code) != 4:
            continue

        # ✔ 排除明顯 ETF（00開頭）
        if code.startswith("00"):
            continue

        stocks.append(code + ".TW")

        if len(stocks) >= limit:
            break

    # 🧠 保底機制（避免空）
    if len(stocks) < 20:
        return [c + ".TW" for c in raw[:50] if c.isdigit()]

    return stocks
