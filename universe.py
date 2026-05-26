import requests
import pandas as pd


def build_universe(percentile=0.2):

    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        data = requests.get(url, timeout=10).json()

        df = pd.DataFrame(data)

        # 基本清理
        df = df[df["Code"].astype(str).str.isdigit()]
        df = df[df["Code"].astype(str).str.len() == 4]

        # ETF 排除（簡化版，避免誤殺）
        df = df[~df["Name"].astype(str).str.contains("ETF|ETN", na=False)]

        # 防欄位錯
        if "TradeVolume" not in df.columns:
            df["TradeVolume"] = 0
        if "TradeValue" not in df.columns:
            df["TradeValue"] = 0

        df["TradeVolume"] = pd.to_numeric(df["TradeVolume"], errors="coerce").fillna(0)
        df["TradeValue"] = pd.to_numeric(df["TradeValue"], errors="coerce").fillna(0)

        # 流動性分數
        df["score"] = df["TradeVolume"] + df["TradeValue"]

        df = df.sort_values("score", ascending=False)

        cutoff = max(int(len(df) * percentile), 80)  # 🔥 保底80檔

        df = df.head(cutoff)

        return [str(c) + ".TW" for c in df["Code"]]

    except:
        # 🧠 絕對保底
        return [
            "2330.TW", "2317.TW", "2454.TW",
            "2412.TW", "2303.TW", "2881.TW",
            "2891.TW", "1303.TW"
        ]
