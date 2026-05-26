import requests


# =========================
# 🧠 法人級股票池（完整版）
# =========================
def build_universe():

    # TWSE 上市股票清單（最乾淨來源）
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"

    data = requests.get(url, timeout=10).json()

    stocks = []

    for i in data:

        code = i.get("公司代號", "")
        name = i.get("公司名稱", "")

        # =========================
        # ① 基本合法性
        # =========================
        if not code:
            continue

        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        # =========================
        # ② ETF / ETN / 指數排除（核心）
        # =========================
        name = str(name)

        if any(x in name for x in [
            "ETF", "ETN", "指數", "槓桿", "反向", "債券"
        ]):
            continue

        # =========================
        # ③ 代碼保護（避免 ETF 殘留）
        # =========================
        if code.startswith(("00", "006", "008", "009")):
            continue

        stocks.append(code + ".TW")

    # =========================
    # 🧠 保底機制（避免空池）
    # =========================
    if len(stocks) < 100:
        fallback_url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        raw = requests.get(fallback_url, timeout=10).json()

        fallback = [
            i["Code"] + ".TW"
            for i in raw
            if i["Code"].isdigit()
        ]

        return fallback[:300]

    return stocks
