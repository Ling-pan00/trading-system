import requests


# =========================
# 📊 取得全市場
# =========================
def get_raw():

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    return data


# =========================
# 🧠 法人級股票池（不混 ETF）
# =========================
def build_institution_universe(limit=120):

    raw = get_raw()

    stocks = []

    for i in raw:

        code = i.get("Code", "")
        name = i.get("Name", "")

        # =========================
        # ① 基本合法性
        # =========================
        if not code.isdigit():
            continue

        if len(code) != 4:
            continue

        # =========================
        # ② ETF / ETN / 指數排除（關鍵）
        # =========================
        name_upper = name.upper()

        if any(x in name_upper for x in [
            "ETF", "ETN", "指數", "槓桿", "反向", "債券"
        ]):
            continue

        # 代碼層級再保護（台股ETF常見區間）
        if (
            code.startswith("00") or
            code.startswith("006") or
            code.startswith("008") or
            code.startswith("009")
        ):
            continue

        stocks.append(code + ".TW")

        if len(stocks) >= limit:
            break

    # =========================
    # 🧠 保底機制（永遠不空）
    # =========================
    if len(stocks) < 30:
        fallback = [i["Code"] for i in raw if i["Code"].isdigit()][:80]
        return [c + ".TW" for c in fallback]

    return stocks
