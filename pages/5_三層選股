import pandas as pd

class ThreePoolEngine:

    def __init__(self, mode="after"):
        """
        mode:
        - "intraday" = 盤中
        - "after" = 盤後
        """
        self.mode = mode

    # =========================
    # 📊 技術指標
    # =========================
    def prepare(self, df):

        df = df.copy()

        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()

        return df

    # =========================
    # 🟡 第一池：洗盤轉強
    # =========================
    def pool1(self, df):

        df = self.prepare(df)

        ma20_up = df['ma20'] > df['ma20'].shift(1)

        # 跌破後回來（簡化版）
        broke = (df['close'] < df['ma5']).rolling(10).max()

        first_rebound = (
            (df['close'] > df['ma5']) &
            (df['close'].shift(1) <= df['ma5'].shift(1))
        )

        # 量能條件（盤中才嚴格）
        if self.mode == "intraday":
            vol_ok = df['volume'] >= df['volume'].shift(1) * 0.8
        else:
            vol_ok = True

        return (
            ma20_up.iloc[-1] and
            (broke.iloc[-1] == 1) and
            first_rebound.iloc[-1] and
            vol_ok.iloc[-1]
        )

    # =========================
    # 🟠 第二池：回測確認
    # =========================
    def pool2(self, df):

        df = self.prepare(df)

        trend = df['close'] > df['ma5']

        pullback = df['low'] <= df['ma5']

        hold = df['close'] > df['ma5']

        vol_ok = True

        if self.mode == "intraday":
            vol_ok = df['volume'] >= df['volume'].shift(1) * 0.8

        return (
            trend.iloc[-1] and
            pullback.iloc[-1] and
            hold.iloc[-1] and
            vol_ok.iloc[-1]
        )

    # =========================
    # 🔴 第三池：主升段
    # =========================
    def pool3(self, df):

        df = self.prepare(df)

        trend = df['close'] > df['ma20']

        structure = (
            (df['ma5'] > df['ma10']) &
            (df['ma10'] > df['ma20'])
        )

        not_break = df['close'] > df['ma10']

        return (
            trend.iloc[-1] and
            structure.iloc[-1] and
            not_break.iloc[-1]
        )

    # =========================
    # 📡 單股分類
    # =========================
    def classify(self, df):

        if self.pool3(df):
            return "🔴 第三池（主升段）"

        elif self.pool2(df):
            return "🟠 第二池（回測確認）"

        elif self.pool1(df):
            return "🟡 第一池（洗盤轉強）"

        else:
            return "⚪ 未入池"

    # =========================
    # 📊 全市場掃描
    # =========================
    def scan_market(self, market_dict):

        result = {
            "pool1": [],
            "pool2": [],
            "pool3": []
        }

        for stock, df in market_dict.items():

            try:
                if self.pool3(df):
                    result["pool3"].append(stock)

                elif self.pool2(df):
                    result["pool2"].append(stock)

                elif self.pool1(df):
                    result["pool1"].append(stock)

            except:
                continue

        return result
