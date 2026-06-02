import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# ======================
# 下載證交所投信資料
# ======================

def get_twse_investment(date_str):

    url = (
        "https://www.twse.com.tw/rwd/zh/fund/TWT44U"
        f"?date={date_str}&response=json"
    )

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if "data" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data["data"],
            columns=data["fields"]
        )

        df["日期"] = date_str

        return df

    except:
        return pd.DataFrame()


# ======================
# 取得最近N天資料
# ======================

def download_days(days=60):

    all_data = []

    today = datetime.today()

    for i in range(days):

        d = today - timedelta(days=i)

        date_str = d.strftime("%Y%m%d")

        print("下載:", date_str)

        df = get_twse_investment(date_str)

        if len(df) > 0:
            all_data.append(df)

        time.sleep(0.3)

    return pd.concat(all_data, ignore_index=True)


# ======================
# 數字清理
# ======================

def clean_number(x):

    try:
        return int(str(x).replace(",", ""))
    except:
        return 0


# ======================
# 主流程
# ======================

df = download_days(60)

# 欄位名稱可能因證交所格式調整而略有不同
stock_col = "證券代號"
buy_col = "投信買賣超股數"

df[buy_col] = df[buy_col].apply(clean_number)

# 張數
df["買賣超張數"] = df[buy_col] / 1000

# 日期排序
df["日期"] = pd.to_datetime(df["日期"])

df = df.sort_values(
    ["證券代號", "日期"]
)

# ======================
# 計算連買天數
# ======================

result = []

for stock, g in df.groupby(stock_col):

    g = g.sort_values("日期")

    streak = 0

    for value in reversed(g["買賣超張數"].tolist()):

        if value > 0:
            streak += 1
        else:
            break

    recent20 = g.tail(20)

    recent60 = g.tail(60)

    result.append({
        "股票": stock,
        "連買天數": streak,
        "近20日買超": recent20["買賣超張數"].sum(),
        "近60日買超": recent60["買賣超張數"].sum()
    })

rank_df = pd.DataFrame(result)

# ======================
# 鎖碼分數
# ======================

rank_df["分數"] = (
    rank_df["連買天數"] * 3
    + rank_df["近20日買超"] * 0.02
    + rank_df["近60日買超"] * 0.01
)

rank_df = rank_df.sort_values(
    "分數",
    ascending=False
)

print(rank_df.head(50))

rank_df.to_excel(
    "投信鎖碼排行.xlsx",
    index=False
)

print("完成")
