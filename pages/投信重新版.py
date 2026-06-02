import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

st.set_page_config(
    page_title="投信鎖碼股排行",
    layout="wide"
)

st.title("投信鎖碼股排行（免費版 V2）")

# =========================
# 下載單日資料
# =========================

@st.cache_data(ttl=3600)
def get_day_data(date_str):

    url = (
        "https://www.twse.com.tw/rwd/zh/fund/TWT44U"
        f"?date={date_str}&response=json"
    )

    try:

        r = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
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


# =========================
# 數字轉換
# =========================

def to_number(x):

    try:

        return int(
            str(x)
            .replace(",", "")
            .replace("+", "")
            .replace(" ", "")
        )

    except:

        return 0


# =========================
# 下載歷史資料
# =========================

@st.cache_data(ttl=3600)
def load_data(days):

    all_data = []

    today = datetime.today()

    for i in range(days):

        d = today - timedelta(days=i)

        date_str = d.strftime("%Y%m%d")

        df = get_day_data(date_str)

        if not df.empty:
            all_data.append(df)

        time.sleep(0.05)

    if len(all_data) == 0:
        return pd.DataFrame()

    return pd.concat(
        all_data,
        ignore_index=True
    )


# =========================
# UI
# =========================

days = st.slider(
    "回溯天數",
    20,
    90,
    60
)

min_streak = st.slider(
    "最低連買天數",
    1,
    20,
    5
)

min_buy20 = st.number_input(
    "近20日最低買超張數",
    value=1000
)

# =========================
# 執行
# =========================

if st.button("開始篩選"):

    with st.spinner("下載資料中..."):

        df = load_data(days)

    if df.empty:

        st.error("抓不到資料")

        st.stop()

    stock_col = "證券代號"

    buy_col = None

    for c in df.columns:

        if "買賣超" in c:

            buy_col = c
            break

    if buy_col is None:

        st.error("找不到投信買賣超欄位")

        st.stop()

    df[buy_col] = df[buy_col].apply(to_number)

    # 股 -> 張
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

        buy20 = g.tail(20)["買超張數"].sum()

        buy60 = g.tail(60)["買超張數"].sum()

        score = (
            streak * 10
            + buy20 * 0.02
            + buy60 * 0.01
        )

        result.append({
            "股票代號": stock,
            "投信連買天數": streak,
            "近20日買超張數": round(buy20),
            "近60日買超張數": round(buy60),
            "鎖碼分數": round(score, 2)
        })

    rank_df = pd.DataFrame(result)

    # =========================
    # 篩選
    # =========================

    rank_df = rank_df[
        (rank_df["投信連買天數"] >= min_streak)
        &
        (rank_df["近20日買超張數"] >= min_buy20)
    ]

    rank_df = rank_df.sort_values(
        ["鎖碼分數"],
        ascending=False
    )

    st.success(
        f"找到 {len(rank_df)} 檔符合條件"
    )

    st.dataframe(
        rank_df,
        use_container_width=True,
        hide_index=True
    )

    csv = rank_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="下載CSV",
        data=csv,
        file_name="投信鎖碼排行.csv",
        mime="text/csv"
    )
