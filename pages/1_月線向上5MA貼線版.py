import pandas as pd
import numpy as np

class ThreePoolEngine:

    def __init__(self):
        pass

    # =====================
    # 技術指標
    # =====================
    def prepare(self, df):

        df = df.copy()

        df["ma5"] = df["close"].rolling(5).mean()
        df["ma10"] = df["close"].rolling(10).mean()
        df["ma20"] = df["close"].rolling(20).mean()

        df["vol_ma20"] = (
            df["volume"]
            .rolling(20)
            .mean()
        )

        return df

    # =====================
    # 第一池
    # =====================
    def pool1(self, df):

        df = self.prepare(df)

        if len(df) < 30:
            return False

        ma20_up = (
            df["ma20"].iloc[-1]
            >
            df["ma20"].iloc[-2]
        )

        broke = (
            (df["close"] < df["ma5"])
            .tail(10)
            .any()
        )

        rebound = (
            df["close"].iloc[-1]
            >
            df["ma5"].iloc[-1]
        )

        vol_ok = (
            df["volume"].iloc[-1]
            >=
            df["volume"].iloc[-2] * 0.8
        )

        body = abs(
            df["close"].iloc[-1]
            -
            df["open"].iloc[-1]
        )

        upper_shadow = (
            df["high"].iloc[-1]
            -
            max(
                df["open"].iloc[-1],
                df["close"].iloc[-1]
            )
        )

        shadow_ok = (
            upper_shadow <= body * 1.5
        )

        return all([
            ma20_up,
            broke,
            rebound,
            vol_ok,
            shadow_ok
        ])

    # =====================
    # 第二池
    # =====================
    def pool2(self, df):

        df = self.prepare(df)

        if len(df) < 30:
            return False

        ma20_up = (
            df["ma20"].iloc[-1]
            >
            df["ma20"].iloc[-2]
        )

        trend = (
            df["close"].iloc[-1]
            >
            df["ma5"].iloc[-1]
        )

        pullback = (
            df["low"].iloc[-1]
            <=
            df["ma5"].iloc[-1] * 1.01
        )

        hold = (
            df["close"].iloc[-1]
            >
            df["ma5"].iloc[-1]
        )

        vol_ok = (
            df["volume"].iloc[-1]
            >=
            df["volume"].iloc[-2] * 0.8
        )

        return all([
            ma20_up,
            trend,
            pullback,
            hold,
            vol_ok
        ])

    # =====================
    # 第三池
    # =====================
    def pool3(self, df):

        df = self.prepare(df)

        if len(df) < 30:
            return False

        ma20_up = (
            df["ma20"].iloc[-1]
            >
            df["ma20"].iloc[-2]
        )

        trend = (
            df["close"].iloc[-1]
            >
            df["ma20"].iloc[-1]
        )

        structure = (
            df["ma5"].iloc[-1]
            >
            df["ma10"].iloc[-1]
            >
            df["ma20"].iloc[-1]
        )

        not_break = (
            df["close"].iloc[-1]
            >
            df["ma10"].iloc[-1]
        )

        volume_ratio = (
            df["volume"].iloc[-1]
            /
            max(df["vol_ma20"].iloc[-1], 1)
        )

        body_pct = (
            (
                df["close"].iloc[-1]
                -
                df["open"].iloc[-1]
            )
            /
            df["open"].iloc[-1]
        )

        not_exhaust = not (
            body_pct > 0.09
            and
            volume_ratio > 3
        )

        return all([
            ma20_up,
            trend,
            structure,
            not_break,
            not_exhaust
        ])

    # =====================
    # 排名
    # =====================

    def score_pool1(self, df):

        df = self.prepare(df)

        return (
            df["volume"].iloc[-1]
            /
            max(
                df["vol_ma20"].iloc[-1],
                1
            )
        )

    def score_pool2(self, df):

        df = self.prepare(df)

        return (
            1
            /
            (
                abs(
                    df["close"].iloc[-1]
                    /
                    df["ma5"].iloc[-1]
                    - 1
                )
                + 0.001
            )
        )

    def score_pool3(self, df):

        if len(df) < 20:
            return 0

        return (
            df["close"].iloc[-1]
            /
            df["close"].iloc[-20]
            - 1
        )

    # =====================
    # 進出場
    # =====================

    def trade_plan(self, pool, df):

        df = self.prepare(df)

        buy = df["close"].iloc[-1]

        if pool == 1:

            stop = df["low"].iloc[-1]

            risk = buy - stop

            target = buy + risk * 2

        elif pool == 2:

            stop = df["ma5"].iloc[-1]

            risk = buy - stop

            target = buy + risk * 2.5

        else:

            stop = df["ma10"].iloc[-1]

            risk = buy - stop

            target = buy + risk * 3

        return {
            "買進價": round(buy, 2),
            "停損價": round(stop, 2),
            "目標價": round(target, 2)
        }

    # =====================
    # 全市場掃描
    # =====================

    def scan_market(self, market_dict):

        pool1_list = []
        pool2_list = []
        pool3_list = []

        for stock, df in market_dict.items():

            try:

                if len(df) < 60:
                    continue

                close = df["close"].iloc[-1]
                volume = df["volume"].iloc[-1]

                # 流動性過濾
                if close < 20:
                    continue

                if volume < 1000:
                    continue

                if self.pool3(df):

                    score = self.score_pool3(df)

                    pool3_list.append(
                        (stock, score, df)
                    )

                elif self.pool2(df):

                    score = self.score_pool2(df)

                    pool2_list.append(
                        (stock, score, df)
                    )

                elif self.pool1(df):

                    score = self.score_pool1(df)

                    pool1_list.append(
                        (stock, score, df)
                    )

            except Exception:
                continue

        pool1_list = sorted(
            pool1_list,
            key=lambda x: x[1],
            reverse=True
        )[:10]

        pool2_list = sorted(
            pool2_list,
            key=lambda x: x[1],
            reverse=True
        )[:10]

        pool3_list = sorted(
            pool3_list,
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "第一池": self.make_table(1, pool1_list),
            "第二池": self.make_table(2, pool2_list),
            "第三池": self.make_table(3, pool3_list)
        }

    # =====================
    # 輸出表
    # =====================

    def make_table(self, pool, data):

        rows = []

        for stock, score, df in data:

            plan = self.trade_plan(pool, df)

            rows.append({
                "股票": stock,
                "分數": round(score, 2),
                "買進價": plan["買進價"],
                "停損價": plan["停損價"],
                "目標價": plan["目標價"]
            })

        return pd.DataFrame(rows)
