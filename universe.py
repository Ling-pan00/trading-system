def build_universe():

    # 🧠 台股「純股票合理範圍」
    # ETF / ETN 幾乎不在這個範圍內

    stocks = []

    for i in range(1100, 9999):

        code = str(i)

        # 排除明顯 ETF 區段
        if code.startswith("00"):
            continue

        if code.startswith("006") or code.startswith("008") or code.startswith("009"):
            continue

        stocks.append(code + ".TW")

    return stocks[:150]
