import requests
import pandas as pd


# =========================
# 🧠 動態流動性股票池
# =========================
def build_universe(top_n=300):

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    df = pd.DataFrame(data)

    # =========================
    # ① 基本清理
    # =========================
    df = df[df["Code"].str.isdigit()]
    df = df[df["Code"].str.len() == 4]

    # =========================
    # ② ETF / ETN 排除
    # =========================
    df = df[~df["Name"].str.contains(
        "ETF|ETN|指數|槓桿|反向|債券",
        na=False
    )]

    # =========================
    # ③ 流動性轉換
    # =========================
    df["TradeVolume"] = pd.to_numeric(df["TradeVolume"], errors="coerce")
    df["TradeValue"] = pd.to_numeric(df["TradeValue"], errors="coerce")

    df = df.dropna(subset=["TradeVolume", "TradeValue"])

    # =========================
    # ④ 流動性分數（法人核心）
    # =========================
    df["LiquidityScore"] = (
        df["TradeVolume"] * 0.6 +
        df["TradeValue"] * 0.4
    )

    # =========================
    # ⑤ 排序選 Top N
    # =========================
    df = df.sort_values("LiquidityScore", ascending=False)

    universe = df["Code"].head(top_n).tolist()

    return [c + ".TW" for c in universe]
