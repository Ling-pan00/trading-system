import requests


# =========================
# 📊 取得全市場
# =========================
def get_universe():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return [i["Code"] for i in data if i["Code"].isdigit()]


# =========================
# 🧠 動態股票池（市場活躍度）
# =========================
def build_dynamic_universe():

    raw = get_universe()

    pool = []

    for code in raw:

        # ✔ 只留股票
        if len(code) != 4:
            continue

        if code.startswith("00"):
            continue

        pool.append(code + ".TW")

    return pool
