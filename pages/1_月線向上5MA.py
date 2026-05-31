def classify_pool(s, df, price, ma5, ma10, ma20, open_price):

    try:
        # =========================
        # 基本安全檢查
        # =========================
        if df is None or len(df) < 30:
            return None

        close = df["Close"]
        open_ = df["Open"]
        volume = df["Volume"]

        # 必要欄位檢查
        required_cols = ["ma5", "ma10", "ma20", "vol_ma5"]
        for c in required_cols:
            if c not in df.columns:
                return None

        ma5_series = df["ma5"].dropna()
        ma10_series = df["ma10"].dropna()
        ma20_series = df["ma20"].dropna()

        if len(ma20_series) < 6 or len(ma5_series) < 10:
            return None

        # =========================
        # 🟡 第一池（箭頭 + 洗盤起漲）
        # =========================

        ma20_slope = (ma20_series.iloc[-1] - ma20_series.iloc[-5]) / ma20_series.iloc[-5]
        ma20_up = ma20_slope
