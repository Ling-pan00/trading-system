import requests


# =========================
# 📊 取得「上市股票清單」（乾淨）
# =========================
def get_stock_list():

    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i.get("公司代號", "")

        if not code:
            continue

        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        stocks.append(code + ".TW")

    return stocks


# =========================
# 🧠 法人股票池（乾淨穩定）
# =========================
def build_universe(limit=150):

    stocks = get_stock_list()

    # 保持合理大小（避免太慢）
    stocks = stocks[:limit]

    return stocks
