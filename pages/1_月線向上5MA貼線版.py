import pandas as pd
import numpy as np

class ThreePoolEngine:

    def __init__(self, mode="after"):
        """
        mode:
        - after = 盤後掃描（建池）
        - intraday = 盤中掃描（交易）
        """
        self.mode = mode

    # =========================
    # 📊 技術指標
    # =========================
    def prepare(self, df):

        df = df.copy()
        df = df.sort_index()

        df['ma5'] = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()

        return df

    # =========================
    # 🟡 第一池：洗盤轉強（放寬版）
    # =========================
    def pool1(self, df):

        df = self.prepare(df)

        if len(df) < 20:
            return False

        # 月/中期趨勢（簡化）
        trend_ok = df['ma20'].iloc[-1] > df['ma20'].iloc[-5]

        # 剛站回5MA（關鍵）
        rebound = (
            df['close'].iloc[-1] > df['ma5'].iloc[-1] and
            df['close'].iloc[-2] <= df['ma5'].iloc[-2]
        )

        return bool(trend_ok and rebound)

    # =========================
    # 🟠 第二池：回測確認（核心進場池）
    # =========================
    def pool2(self, df):

        df = self.prepare(df)

        if len(df) < 10:
            return False

        close = df['close'].iloc[-1]
        ma5 = df['ma5'].iloc[-1]
        low = df['low'].iloc[-1]

        # 趨勢已成立（站上5MA）
        trend = close > ma5

        # 回測5MA（允許觸碰）
        pullback = low <= ma5 * 1.01   # 🔥 放寬：避免錯過

        # 收盤守住
        hold = close >= ma5 * 0.995

        return bool(trend and pullback and hold)

    # =========================
    # 🔴 第三池：主升段（順勢）
    # =========================
    def pool3(self, df):

        df = self.prepare(df)

        if len(df) < 20:
            return False

        close = df['close'].iloc[-1]

        trend = close > df['ma20'].iloc[-1]

        structure = (
            df['ma5'].iloc[-1] > df['ma10'].iloc[-1] >
            df['ma20'].iloc[-1]
        )

        # 避免爆量末段（簡化）
        body = abs(df['close'] - df['open'])
        upper = df['high'] - df[['close','open']].max(axis=1)

        not_exhaust = upper.iloc[-1] <= body.iloc[-1] * 1.5

        return bool(trend and structure and not_exhaust)

    # =========================
    # 📡 分類（核心）
    # =========================
    def classify(self, df):

        if self.pool3(df):
            return "🔴 第三池（主升段）"

        elif self.pool2(df):
            return "🟠 第二池（回測進場）"

        elif self.pool1(df):
            return "🟡 第一池（剛轉強）"

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
