import pandas as pd
import numpy as np


class ThreePoolEngine:

    def __init__(self, mode="after"):
        self.mode = mode

    # =====================
    # 技術指標
    # =====================

    def prepare(self, df):

        df = df.copy()

        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()

        df['vol_ma20'] = df['volume'].rolling(20).mean()

        return df

    # =====================
    # 第一池
    # =====================

    def pool1(self, df):

        df = self.prepare(df)

        ma20_up = df['ma20'] > df['ma20'].shift(1)

        broke = (
            (df['close'] < df['ma5'])
            .rolling(10)
            .max()
        )

        first_rebound = (
            (df['close'] > df['ma5']) &
            (df['close'].shift(1) <= df['ma5'].shift(1))
        )

        vol_ok = (
            df['volume']
            >=
            df['volume'].shift(1) * 0.8
        )

        body = abs(df['close'] - df['open'])

        upper_shadow = (
            df['high']
            -
            df[['open', 'close']].max(axis=1)
        )

        shadow_ok = upper_shadow <= body

        return (
            ma20_up.iloc[-1]
            and broke.iloc[-1] == 1
            and first_rebound.iloc[-1]
            and vol_ok.iloc[-1]
            and shadow_ok.iloc[-1]
        )

    # =====================
    # 第二池
    # =====================

    def pool2(self, df):

        df = self.prepare(df)

        ma20_up = df['ma20'] > df['ma20'].shift(1)

        trend = df['close'] > df['ma5']

        pullback = df['low'] <= df['ma5']

        hold = df['close'] > df['ma5']

        vol_ok = (
            df['volume']
            >=
            df['volume'].shift(1) * 0.8
        )

        return (
            ma20_up.iloc[-1]
            and trend.iloc[-1]
            and pullback.iloc[-1]
            and hold.iloc[-1]
            and vol_ok.iloc[-1]
        )

    # =====================
    # 第三池
    # =====================

    def pool3(self, df):

        df = self.prepare(df)

        ma20_up = df['ma20'] > df['ma20'].shift(1)

        trend = df['close'] > df['ma20']

        structure = (
            (df['ma5'] > df['ma10'])
            &
            (df['ma10'] > df['ma20'])
        )

        not_break = (
            df['close'] > df['ma10']
        )

        body_pct = (
            (df['close'] - df['open'])
            /
            df['open']
        )

        volume_ratio = (
            df['volume']
            /
            df['vol_ma20']
        )

        not_exhaust = ~(
            (body_pct > 0.07)
            &
            (volume_ratio > 2)
        )

        return (
            ma20_up.iloc[-1]
            and trend.iloc[-1]
            and structure.iloc[-1]
            and not_break.iloc[-1]
            and not_exhaust.iloc[-1]
        )

    # =====================
    # 排名分數
    # =====================

    def score_pool1(self, df):

        df = self.prepare(df)

        return (
            df['volume'].iloc[-1]
            /
            df['vol_ma20'].iloc[-1]
        )

    def score_pool2(self, df):

        df = self.prepare(df)

        return abs(
            df['close'].iloc[-1]
            /
            df['ma5'].iloc[-1]
            - 1
        )

    def score_pool3(self, df):

        df = self.prepare(df)

        return (
            df['close'].iloc[-1]
            /
            df['close'].iloc[-20]
            - 1
        )

    # =====================
    # 進出場規劃
    # =====================

    def trade_plan(self, pool, df):

        df = self.prepare(df)

        close = df['close'].iloc[-1]
        low = df['low'].iloc[-1]

        ma5 = df['ma5'].iloc[-1]
        ma10 = df['ma10'].iloc[-1]

        if pool == 1:

            buy = close
            stop = low

            target = close * 1.15

        elif pool == 2:

            buy = close

            stop = ma5

            target = close * 1.20

        else:

            recent_high = (
                df['high']
                .rolling(20)
                .max()
                .iloc[-1]
            )

            buy = recent_high

            stop = ma10

            target = buy * 1.25

        return {
            'buy': round(buy, 2),
            'stop': round(stop, 2),
            'target': round(target, 2)
        }

    # =====================
    # 掃描市場
    # =====================

    def scan_market(self, market_dict):

        p1 = []
        p2 = []
        p3 = []

        for stock, df in market_dict.items():

            try:

                if self.pool3(df):

                    score = self.score_pool3(df)

                    p3.append(
                        (stock, score, df)
                    )

                elif self.pool2(df):

                    score = self.score_pool2(df)

                    p2.append(
                        (stock, score, df)
                    )

                elif self.pool1(df):

                    score = self.score_pool1(df)

                    p1.append(
                        (stock, score, df)
                    )

            except:
                pass

        p1 = sorted(
            p1,
            key=lambda x: x[1],
            reverse=True
        )[:10]

        p2 = sorted(
            p2,
            key=lambda x: x[1]
        )[:10]

        p3 = sorted(
            p3,
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "第一池": self.build_output(1, p1),
            "第二池": self.build_output(2, p2),
            "第三池": self.build_output(3, p3)
        }

    # =====================
    # 建立輸出
    # =====================

    def build_output(self, pool, stocks):

        rows = []

        for stock, score, df in stocks:

            tp = self.trade_plan(pool, df)

            rows.append({

                "股票": stock,

                "分數": round(score, 3),

                "買進價": tp['buy'],

                "停損價": tp['stop'],

                "目標價": tp['target']
            })

        return pd.DataFrame(rows)
