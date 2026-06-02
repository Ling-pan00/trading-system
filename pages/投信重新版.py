import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

st.set_page_config(
    page_title="投信鎖碼股排行",
    layout="wide"
)

st.title("投信鎖碼股排行（免費版）")

# -----------------------
# API
# -----------------------

@st.cache_data(ttl=3600)
def get_day_data(date_str):

    url = (
        "https://www.twse.com.tw/rwd/zh/fund/TWT44U"
        f"?date={date_str}&response=json"
    )

    try:

        r = requests.get(
            url,
            timeout=10
        )

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


# -----------------------
# 數字轉換
# -----------------------

def to_number(x):

    try:
        return int(
            str(x)
            .replace(",", "")
            .replace("+", "")
        )

    except:
        return 0


# -----------------------
# 抓最近交易資料
# -----------------------

@st.cache_data(ttl=3600)
def load_data(days=30):

    data_list = []

    today = datetime.today()

    progress = st.progress(0)

    for i in range(days):

        d = today - timedelta(days=i)

        date_str = d.strftime("%Y%m%d")

        df = get_day_data(date_str)

        if not df.empty:
            data_list.append(df)

        progress.progress((i + 1) / days)

        time.sleep(0.05)

    progress.empty()

    if len(data_list) == 0:
        return pd.DataFrame()

    return pd.concat(
        data_list,
        ignore_index=True
    )


# -----------------------
# 天數選擇
# -----------------------

days = st.slider(
    "回溯天數",
    20,
    90,
    60
)

if st.button("開始篩選"):

    with st.spinner("下載資料中..."):

        df = load_data(days)

    if df.empty:

        st.error("無法取得資料")

        st.stop()

    stock_col = "證券代號"

    # 找投信買賣超欄位
    buy_col = None

    for c in df.columns:

        if "買賣超" in c:

            buy_col = c
            break

    if buy_col is None:

        st.error("找不到投信買賣超欄位")

        st.stop()

    df[buy_col] = df[buy_col].apply(to_number)

    df["買超張數"] = df[buy_col] / 1000

    df["日期"] = pd.to_datetime(df["日期"])

    result = []

    for stock, g in df.groupby(stock_col):

        g = g.sort_values("日期")

        streak = 0

        values = g["買超張數"].tolist()

        for v in reversed(values):

            if v > 0:
                streak += 1
            else:
                break

        recent20 = g.tail(20)

        recent60 = g.tail(60)

        score = (
            streak * 5
            + recent20["買超張數"].sum() * 0.02
            + recent60["買超張數"].sum() * 0.01
        )

        result.append({
            "股票代號": stock,
            "投信連買天數": streak,
            "近20日買超": round(
                recent20["買超張數"].sum(),
                0
            ),
            "近60日買超": round(
                recent60["買超張數"].sum(),
                0
            ),
            "鎖碼分數": round(
                score,
                2
            )
        })

    rank_df = pd.DataFrame(result)

    rank_df = rank_df.sort_values(
        "鎖碼分數",
        ascending=False
    )

    st.subheader("Top 50")

    st.dataframe(
        rank_df.head(50),
        use_container_width=True
    )

    csv = rank_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "下載CSV",
        csv,
        "投信鎖碼排行.csv",
        "text/csv"
    )
