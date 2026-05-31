def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 30:
        return None

    # =========================
    # 🧱 基礎防呆（避免 yfinance 爆炸）
    # =========================
    try:
        close = df["Close"]
        open_ = df["Open"]
        volume = df["Volume"]

        ma5_series = df["ma5"]
        ma10_series = df["ma10"]
        ma20_series = df["ma20"]

        if len(close) < 10:
            return None

    except:
        return None

    # =========================
    # 🟡 第一池（箭頭 + 洗盤起漲）
    # =========================

    ma20_valid = ma20_series.dropna()
    if len(ma20_valid) < 6:
        return None

    # 📈 MA20箭頭（穩定上升）
    ma20_slope = (ma20_valid.iloc[-1] - ma20_valid.iloc[-5]) / ma20_valid.iloc[-5]
    ma20_up = ma20_slope > 0.003

    # 📈 站上月線
    above_ma20 = price > ma20

    # 🧹 洗盤後站回MA5
    was_below_ma5 = (close.iloc[-10:] < ma5_series.iloc[-10:]).any()
    reclaim_ma5 = was_below_ma5 and (price > ma5)

    # 🔥 當日轉強（安全版）
    if pd.isna(open_.iloc[-1]) or pd.isna(close.iloc[-1]):
        return None

    red_k = close.iloc[-1] > open_.iloc[-1]
    momentum = close.iloc[-1] > close.iloc[-2]

    # 📊 量能確認（安全版）
    vol_now = volume.iloc[-1]
    vol_ma = df["vol_ma5"].iloc[-1]

    if pd.isna(vol_now) or pd.isna(vol_ma):
        return None

    vol_ok = vol_now > vol_ma

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

    ma20_trend = ma20_series.iloc[-1] > ma20_series.iloc[-10]

    trend_align = (ma5 > ma10) and (ma10 > ma20)

    score_ok = s >= 4

    pool2 = (
        ma20_trend
        and above_ma20
        and trend_align
        and score_ok
        and vol_ok
    )

    # =========================
    # 🔵 第三池（原樣保留）
    # =========================
    ma20_series_clean = ma20_series.dropna()
    if len(ma20_series_clean) < 5:
        return None

    month_up = ma20_series_clean.iloc[-1] > ma20_series_clean.iloc[-5]

    pool3 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 5

    # =========================
    # 🔴 第四池（原樣保留）
    # =========================
    accel = close.pct_change().tail(3).mean() > 0
    vol_break = vol_now > vol_ma

    pool4 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 6 and accel and vol_break

    # =========================
    # 回傳優先級
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
