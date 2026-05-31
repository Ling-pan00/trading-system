def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 30:
        return None

    ma20_series = df["ma20"].dropna()

    if len(ma20_series) < 10:
        return None

    # =========================
    # 基礎條件
    # =========================

    above_ma20 = price > ma20
    ma20_up = ma20_series.iloc[-1] > ma20_series.iloc[-10]
    trend_align = (ma5 > ma10 > ma20)

    red_k = df["Close"].iloc[-1] > df["Open"].iloc[-1]
    vol_ok = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

    accel = df["Close"].pct_change().tail(3).mean() > 0

    not_early = (df["Close"].iloc[-10:] > df["ma5"].iloc[-10:]).all()

    # =========================
    # 🔴 第四池（最強爆發）
    # =========================

    pool4 = (
        ma20_up and above_ma20 and trend_align
        and accel and vol_ok and s >= 6
    )

    if pool4:
        return "🔴 第四池"

    # =========================
    # 🔵 第三池（加速段）
    # =========================

    pool3 = (
        ma20_up and above_ma20 and trend_align
        and not_early and accel
        and s >= 5
    )

    if pool3:
        return "🔵 第三池"

    # =========================
    # 🟠 第二池（趨勢段）
    # =========================

    pool2 = (
        ma20_up and above_ma20 and trend_align
        and s >= 4
    )

    if pool2:
        return "🟠 第二池"

    # =========================
    # 🟡 第一池（起漲）
    # =========================

    ma5_series = df["ma5"].dropna()

    was_below_ma5 = (df["Close"].iloc[-15:] < ma5_series.iloc[-15:]).any()
    reclaim_ma5 = price > ma5

    pool1 = (
        ma20_up
        and above_ma20
        and was_below_ma5
        and reclaim_ma5
        and red_k
    )

    if pool1:
        return "🟡 第一池"

    return None
