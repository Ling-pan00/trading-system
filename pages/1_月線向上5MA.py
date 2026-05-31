def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    if df is None or len(df) < 30:
        return None

    try:
        # =========================
        # 防呆：避免欄位不存在
        # =========================
        required = ["ma5", "ma10", "ma20", "vol_ma5"]
        for c in required:
            if c not in df.columns:
                return None

        if len(df["ma20"].dropna()) < 15:
            return None

        # =========================
        # 基本序列（不 dropna 避免錯位）
        # =========================
        ma20_series = df["ma20"]
        ma5_series = df["ma5"]

        # =========================
        # 安全取值（避免 iloc 爆）
        # =========================
        if len(df) < 20:
            return None

        # =========================
        # 共用條件
        # =========================
        above_ma20 = price > ma20

        ma20_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]

        trend_align = (ma5 > ma10 > ma20)

        red_k = df["Close"].iloc[-1] > df["Open"].iloc[-1]

        vol_ok = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]

        accel = df["Close"].pct_change().tail(3).mean() > 0

        # =========================
        # 🔴 第四池
        # =========================
        if len(df) >= 10:
            pool4 = ma20_up and above_ma20 and trend_align and accel and vol_ok and s >= 6
            if pool4:
                return "🔴 第四池"

        # =========================
        # 🔵 第三池
        # =========================
        if len(df) >= 10:
            not_early = (df["Close"].iloc[-10:] > df["ma5"].iloc[-10:]).all()
            pool3 = ma20_up and above_ma20 and trend_align and not_early and accel and s >= 5
            if pool3:
                return "🔵 第三池"

        # =========================
        # 🟠 第二池
        # =========================
        pool2 = ma20_up and above_ma20 and trend_align and s >= 4
        if pool2:
            return "🟠 第二池"

        # =========================
        # 🟡 第一池
        # =========================
        if len(df) >= 15:
            was_below_ma5 = (df["Close"].iloc[-15:] < df["ma5"].iloc[-15:]).any()
            reclaim_ma5 = price > ma5

            pool1 = ma20_up and above_ma20 and was_below_ma5 and reclaim_ma5 and red_k
            if pool1:
                return "🟡 第一池"

        return None

    except:
        return None
