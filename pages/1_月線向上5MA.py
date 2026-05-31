def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    try:
        if df is None or len(df) < 30:
            return None

        close = df["Close"]
        open_ = df["Open"]
        volume = df["Volume"]

        # =========================
        # 🟡 第一池（安全版）
        # =========================

        if "ma20" not in df.columns or "ma5" not in df.columns:
            return None

        ma20_series = df["ma20"].dropna()
        ma5_series = df["ma5"].dropna()

        if len(ma20_series) < 6 or len(ma5_series) < 10:
            return None

        ma20_slope = (ma20_series.iloc[-1] - ma20_series.iloc[-5]) / ma20_series.iloc[-5]
        ma20_up = ma20_slope > 0.003

        above_ma20 = price > ma20

        was_below_ma5 = (close.iloc[-10:] < ma5_series.iloc[-10:]).any()
        reclaim_ma5 = was_below_ma5 and (price > ma5)

        if pd.isna(open_.iloc[-1]) or pd.isna(close.iloc[-1]):
            return None

        red_k = close.iloc[-1] > open_.iloc[-1]
        momentum = close.iloc[-1] > close.iloc[-2]

        vol_ma5 = df["vol_ma5"].iloc[-1]
        vol_now = volume.iloc[-1]

        if pd.isna(vol_ma5) or pd.isna(vol_now):
            return None

        vol_ok = vol_now > vol_ma5

        pool1 = (
            ma20_up
            and above_ma20
            and reclaim_ma5
            and red_k
            and momentum
            and vol_ok
        )

        # =========================
        # 🟠 第二池（安全版）
        # =========================

        if len(ma20_series) < 10:
            return None

        ma20_trend = ma20_series.iloc[-1] > ma20_series.iloc[-10]

        trend_align = (ma5 > ma10 > ma20)

        score_ok = s >= 4

        pool2 = (
            ma20_trend
            and above_ma20
            and trend_align
            and score_ok
            and vol_ok
        )

        # =========================
        # 🔵🔴（維持原邏輯）
        # =========================

        month_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]

        pool3 = month_up and above_ma20 and (ma5 > ma10 > ma20) and s >= 5

        accel = close.pct_change().tail(3).mean() > 0
        vol_break = vol_now > vol_ma5

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

    except:
        return None
