import requests
import pandas as pd


def build_universe(top_n=300):

    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    data = requests.get(url, timeout=10).json()

    df = pd.DataFrame(data)

    df = df[df["Code"].str.isdigit()]
    df = df[df["Code"].str.len() == 4]

    df = df[~df["Name"].str.contains(
        "ETF|ETN|指數|槓桿|反向|債券",
        na=False
    )]

    df["TradeVolume"] = pd.to_numeric(df["TradeVolume"], errors="coerce")
    df["TradeValue"] = pd.to_numeric(df["TradeValue"], errors="coerce")

    df = df.dropna(subset=["TradeVolume", "TradeValue"])

    df["LiquidityScore"] = df["TradeVolume"] * 0.6 + df["TradeValue"] * 0.4

    df = df.sort_values("LiquidityScore", ascending=False)

    return (df["Code"].head(top_n) + ".TW").tolist()
