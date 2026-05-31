def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 25:
        return None

    ma20_series = df["ma20"].dropna()
    if len(ma20_series) < 5:
        return None

    # =========================
    # 趨勢條件
    # =========================
    month_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]
    above_ma20 = price > ma20

    # =========================
    # 🟡 第一池（修正版：正確邏輯）
    # =========================
    # 曾經跌破5MA（不限時間）
    dipped = (df["Close"] < df["ma5"]).any()

    # 現在站回5MA
    reclaim_ma5 = price > ma5

    # 紅K
    red_k = price > open_price

    pool1 = month_up and above_ma20 and dipped and reclaim_ma5 and red_k


    # =========================
    # 🟠 第二池
    # =========================
    pool2 = month_up and above_ma20 and s >= 4


    # =========================
    # 🔵 第三池
    # =========================
    pool3 = month_up and above_ma20 and ma5 > ma10 > ma20 and s >= 5


    # =========================
    # 🔴 第四池
    # =========================
    accel = df["Close"].pct_change().tail(3).mean() > 0
    vol_break = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

    pool4 = (
        month_up and above_ma20 and
        ma5 > ma10 > ma20 and
        s >= 6 and
        accel and
        vol_break
    )


    # =========================
    # 池別優先順序
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
