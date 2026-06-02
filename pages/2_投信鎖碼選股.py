import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# ===================================
# 頁面設定
# ===================================

st.set_page_config(
    page_title="投信鎖碼股 V3 Lite",
    layout="wide"
)

st.title("投信鎖碼股篩選器 V3 Lite")

# ===================================
# API
# ===================================

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

# ===================================
# 數字轉換
# ===================================

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

# ===================================
# 載入歷史資料
# ===================================

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

# ===================================
# UI
# ===================================

days = st.slider(
    "回溯天數",
    min_value=30,
    max_value=90,
    value=60
)

if st.button("開始篩選"):

    with st.spinner("下載資料中..."):

        df = load_data(days)

    if df.empty:

        st.error("無法取得資料")

        st.stop()

    st.success(f"共取得 {len(df):,} 筆資料")

    # ============================
    # 找欄位
    # ============================

    stock_col = "證券代號"

    buy_col = None

    for c in df.columns:

        if "買賣超" in c:

            buy_col = c
            break

    if buy_col is None:

        st.error("找不到投信買賣超欄位")

        st.write(df.columns.tolist())

        st.stop()

    # ============================
    # 整理資料
    # ============================

    df[buy_col] = df[buy_col].apply(to_number)

    # 股數轉張數
    df["買超張數"] = df[buy_col] / 1000

    df["日期"] = pd.to_datetime(df["日期"])

    # ============================
    # 計算
    # ============================

    result = []

    for stock, g in df.groupby(stock_col):

        g = g.sort_values("日期")

        values = g["買超張數"].tolist()

        streak = 0

        for v in reversed(values):

            if v > 0:
                streak += 1
            else:
                break

        buy20 = g.tail(20)["買超張數"].sum()

        buy60 = g.tail(60)["買超張數"].sum()

        result.append({
            "股票代號": stock,
            "投信連買天數": streak,
            "近20日買超張數": round(buy20),
            "近60日買超張數": round(buy60)
        })

    rank_df = pd.DataFrame(result)

    # ============================
    # V3 Lite 條件
    # ============================

    rank_df = rank_df[
        (rank_df["投信連買天數"] >= 3)
        &
        (rank_df["投信連買天數"] <= 8)
        &
        (rank_df["近20日買超張數"] >= 1000)
    ]

    # ============================
    # 鎖碼分數
    # ============================

    rank_df["鎖碼分數"] = (
        rank_df["投信連買天數"] * 50
        +
        rank_df["近20日買超張數"] * 0.01
    )

    rank_df = rank_df.sort_values(
        "鎖碼分數",
        ascending=False
    )

    # ============================
    # 顯示
    # ============================

    st.success(
        f"符合條件股票數：{len(rank_df)}"
    )

    st.dataframe(
        rank_df,
        use_container_width=True,
        hide_index=True
    )

    # ============================
    # CSV下載
    # ============================

    csv = rank_df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="下載CSV",
        data=csv,
        file_name="投信鎖碼股_V3Lite.csv",
        mime="text/csv"
    )
