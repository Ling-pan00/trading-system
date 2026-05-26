import requests
import pandas as pd


# =========================
# 🧠 百分比動態股票池
# =========================
def build_universe(percentile=0.2):  # 20%預設

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

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
    # 數據轉換
    # =========================
    df["TradeVolume"] = pd.to_numeric(df["TradeVolume"], errors="coerce")
    df["TradeValue"] = pd.to_numeric(df["TradeValue"], errors="coerce")

    df = df.dropna(subset=["TradeVolume", "TradeValue"])

    # =========================
    # 流動性分數
    # =========================
    df["LiquidityScore"] = (
        df["TradeVolume"] * 0.6 +
        df["TradeValue"] * 0.4
    )

    df = df.sort_values("LiquidityScore", ascending=False)

    # =========================
    # 🚀 百分比切割（核心）
    # =========================
    cutoff = int(len(df) * percentile)

    df = df.head(cutoff)

    return (df["Code"] + ".TW").tolist()
