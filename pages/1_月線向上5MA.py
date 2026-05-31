def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 25:
        return None

    # =========================
    # 🟡 第一池（箭頭 + 洗盤 + 轉強）
    # =========================

    ma20_series = df["ma20"].dropna()
    ma5_series = df["ma5"].dropna()

    if len(ma20_series) < 6 or len(ma5_series) < 10:
        return None

    # MA20箭頭（向上）
    ma20_up = df["ma20"].iloc[-1] > df["ma20"].iloc[-5]

    # 站上月線
    above_ma20 = price > ma20

    # 曾跌破MA5後收回
    was_below_ma5 = (df["Close"].iloc[-10:] < ma5_series.iloc[-10:]).any()
    reclaim_ma5 = was_below_ma5 and (price > ma5)

    # 紅K + 動能
    red_k = df["Close"].iloc[-1] > df["Open"].iloc[-1]
    momentum = df["Close"].iloc[-1] > df["Close"].iloc[-2]

    # 量能
    vol_ok = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

    pool1 = (
        ma20_up
        and above_ma20
        and reclaim_ma5
        and red_k
        and momentum
        and vol_ok
    )

    # =========================
    # 🟠 第二池（穩定多頭）
    # =========================

    if len(ma20_series) < 10:
        return None

    ma20_trend = df["ma20"].iloc[-1] > df["ma20"].iloc[-10]
    trend_align = (ma5 > ma10) and (ma10 > ma20)

    pool2 = (
        ma20_trend
        and above_ma20
        and trend_align
        and s >= 4
    )

    # =========================
    # 🔵 第三池（原樣）
    # =========================

    month_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]
    pool3 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 5

    # =========================
    # 🔴 第四池（原樣）
    # =========================

    accel = df["Close"].pct_change().tail(3).mean() > 0
    vol_break = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

    pool4 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 6 and accel and vol_break

    # =========================
    # 回傳優先順序
    # =========================

    if pool4:
        return "🔴 第四池"
    elif pool3:
        return "🔵 第三池"
    elif pool2:
        return "🟠 第二池"
    elif pool1:
        return "🟡 第一池"
    else:
        return None
