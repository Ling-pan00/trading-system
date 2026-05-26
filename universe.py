import requests
import pandas as pd


# =========================
# 🧠 終極安全股票池（永不炸 import）
# =========================
def build_universe(top_n=300):

    try:
        url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        data = requests.get(url, timeout=8).json()

        df = pd.DataFrame(data)

        # =========================
        # 基本清理
        # =========================
        df = df[df["Code"].astype(str).str.isdigit()]
        df = df[df["Code"].astype(str).str.len() == 4]

        # =========================
        # ETF / ETN 排除
        # =========================
        df = df[~df["Name"].astype(str).str.contains(
            "ETF|ETN|指數|槓桿|反向|債券",
            na=False
        )]

        # =========================
        # 流動性欄位（保護）
        # =========================
        df["TradeVolume"] = pd.to_numeric(df.get("TradeVolume", 0), errors="coerce")
        df["TradeValue"] = pd.to_numeric(df.get("TradeValue", 0), errors="coerce")

        df = df.dropna(subset=["TradeVolume", "TradeValue"])

        if len(df) == 0:
            raise ValueError("empty universe")

        # =========================
        # 流動性排序
        # =========================
        df["LiquidityScore"] = (
            df["TradeVolume"] * 0.6 +
            df["TradeValue"] * 0.4
        )

        df = df.sort_values("LiquidityScore", ascending=False)

        universe = df["Code"].head(top_n).tolist()

        return [c + ".TW" for c in universe]

    except Exception:
        # =========================
        # 🧠 永遠保底（關鍵）
        # =========================
        return [
            "2330.TW",
            "2317.TW",
            "2454.TW",
            "2412.TW",
            "2303.TW"
        ]
