def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 25:
        return None

    ma20_series = df["ma20"].dropna()
    if len(ma20_series) < 5:
        return None

    # =========================
    # 🟡 第一池（箭頭 + 洗盤起漲）
    # =========================

    # 📈 MA20箭頭（穩定上升）
    ma20_slope = (df["ma20"].iloc[-1] - df["ma20"].iloc[-5]) / df["ma20"].iloc[-5]
    ma20_up = ma20_slope > 0.003

    # 📈 趨勢區
    above_ma20 = price > ma20

    # 🧹 洗盤後站回MA5
    was_below_ma5 = (df["Close"].iloc[-10:] < df["ma5"].iloc[-10:]).any()
    reclaim_ma5 = was_below_ma5 and (price > ma5)

    # 🔥 當日轉強（紅K + 延續）
    red_k = df["Close"].iloc[-1] > df["Open"].iloc[-1]
    momentum = df["Close"].iloc[-1] > df["Close"].iloc[-2]

    # 📊 量能確認
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
    # 🟠 第二池（趨勢確認）
    # =========================

    # 📈 MA20穩定上升
    ma20_trend = df["ma20"].iloc[-1] > df["ma20"].iloc[-10]

    # 📈 多頭排列開始
    trend_align = (ma5 > ma10) and (ma10 > ma20)

    # 📊 仍在多頭區
    above_ma20 = price > ma20

    # 📊 技術分數
    score_ok = s >= 4

    # 📊 量能過濾
    vol_ok = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

    pool2 = (
        ma20_trend
        and trend_align
        and above_ma20
        and score_ok
        and vol_ok
    )

    # =========================
    # 🔵 第三池
    # =========================
    month_up = ma20_series.iloc[-1] > ma20_series.iloc[-min(5, len(ma20_series))]
    pool3 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 5

    # =========================
    # 🔴 第四池
    # =========================
    accel = df["Close"].pct_change().tail(3).mean() > 0
    vol_break = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]
    pool4 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 6 and accel and vol_break

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
