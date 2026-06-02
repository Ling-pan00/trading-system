import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V7.2", layout="wide")
st.title("投信鎖碼股 V7.2（防空修正版）")

# =========================
# TWSE
# =========================
@st.cache_data(ttl=3600)
def get_day_data(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date_str}&response=json"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        # 🔥 關鍵防空1
        if data.get("stat") != "OK":
            return None

        if "data" not in data or "fields" not in data:
            return None

        df = pd.DataFrame(data["data"])

        # 🔥 關鍵防空2（避免欄位不一致）
        if len(df.columns) != len(data["fields"]):
            return None

        df.columns = data["fields"]
        return df

    except:
        return None


@st.cache_data(ttl=3600)
def load_data(days=60):
    all_data = []
    today = datetime.today()

    i = 0
    checked = 0

    while checked < days and i < 150:
        d = today - timedelta(days=i)
        i += 1

        df = get_day_data(d.strftime("%Y%m%d"))

        if df is not None and not df.empty:
            all_data.append(df)
            checked += 1

        time.sleep(0.02)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


# =========================
# utils
# =========================
def find_col(df, keywords):
    for c in df.columns:
        for k in keywords:
            if k in str(c):
                return c
    return None


# =========================
# UI
# =========================
days = st.slider("回溯天數", 40, 100, 60)

if st.button("開始 V7.2"):

    df = load_data(days)

    st.write("原始資料:", df.shape)

    if df.empty:
        st.error("TWSE 完全沒抓到資料（API失敗或被擋）")
        st.stop()

    st.write("欄位:", df.columns.tolist())

    # =========================
    # 🔥 強制找欄位
    # =========================
    stock_col = find_col(df, ["證券代號", "代號"])
    buy_col = find_col(df, ["買賣超"])

    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗")
        st.stop()

    df = df.dropna(subset=[stock_col])

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    # =========================
    # analysis
    # =========================
    for stock, g in df.groupby(stock_col):

        try:
            if str(stock).startswith("00"):
                continue

            g = g.sort_index()

            last10 = g[buy_col].tail(10).sum()
            last20 = g[buy_col].tail(20).sum()

            if last20 == 0:
                continue

            strength = last10 / (abs(last20) + 1)

            result.append({
                "股票代號": stock,
                "強度": strength,
                "last10": last10,
                "last20": last20
            })

        except:
            continue

    rank_df = pd.DataFrame(result)

    if rank_df.empty:
        st.error("結果為空（代表 TWSE 這段時間沒有有效資料）")
        st.stop()

    rank_df = rank_df.sort_values("強度", ascending=False)

    st.success(f"完成：{len(rank_df)} 檔")

    st.dataframe(rank_df, use_container_width=True)
