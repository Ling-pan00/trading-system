import requests
import pandas as pd


def build_universe(percentile=0.2):

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    df = pd.DataFrame(data)

    df = df[df["Code"].astype(str).str.isdigit()]
    df = df[df["Code"].astype(str).str.len() == 4]

    df = df[~df["Name"].astype(str).str.contains(
        "ETF|ETN|指數|槓桿|反向|債券",
        na=False
    )]

    df["TradeVolume"] = pd.to_numeric(df["TradeVolume"], errors="coerce")
    df["TradeValue"] = pd.to_numeric(df["TradeValue"], errors="coerce")

    df = df.dropna(subset=["TradeVolume", "TradeValue"])

    df["LiquidityScore"] = (
        df["TradeVolume"] * 0.6 +
        df["TradeValue"] * 0.4
    )

    df = df.sort_values("LiquidityScore", ascending=False)

    cutoff = int(len(df) * percentile)

    df = df.head(cutoff)

    return (df["Code"] + ".TW").tolist()
