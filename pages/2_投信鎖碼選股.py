import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V7.1", layout="wide")
st.title("投信鎖碼股 V7.1（修正欄位崩潰版）")

# =========================
# TWSE
# =========================
@st.cache_data(ttl=3600)
def get_day_data(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date_str}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if data.get("stat") != "OK":
            return pd.DataFrame()

        return pd.DataFrame(data["data"], columns=data["fields"])

    except:
        return pd.DataFrame()


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

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


# =========================
# utils
# =========================
def find_col(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None


def is_etf(code):
    return str(code).startswith("00")


# =========================
# price
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):
    try:
        t = yf.Ticker(f"{stock}.TW")
        h = t.history(period="6mo")

        if h is None or h.empty:
            return None

        close = h["Close"]
        vol = h["Volume"]

        price = float(close.iloc[-1])
        ma20 = float(close.rolling(20).mean().iloc[-1])

        return {
            "ma_up": ma20 > close.rolling(20).mean().iloc[-5],
            "breakout": price > close.rolling(20).max().iloc[-2],
            "vol_up": vol.iloc[-1] > vol.tail(20).mean()
        }

    except:
        return None


# =========================
# UI
# =========================
days = st.slider("回溯天數", 40, 100, 60)

if st.button("開始 V7.1"):

    df = load_data(days)

    st.write("原始資料:", df.shape)

    if df.empty:
        st.error("TWSE 無資料")
        st.stop()

    # =========================
    # 🔥 正確抓欄位（修正點）
    # =========================
    stock_col = find_col(df, ["證券代號", "代號"])
    buy_col = find_col(df, ["買賣超", "買賣超股數", "買賣超(股)"])

    if stock_col is None or buy_col is None:
        st.error("欄位抓不到（TWSE格式變動）")
        st.write(df.columns)
        st.stop()

    df = df.dropna(subset=[stock_col])

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    for stock, g in df.groupby(stock_col):

        try:
            if is_etf(stock):
                continue

            g = g.sort_index()

            last10 = g[buy_col].tail(10).mean()
            last20 = g[buy_col].tail(20).mean()

            if last20 == 0:
                continue

            strength = last10 / (abs(last20) + 1)

            price = get_price(stock)
            if price is None:
                continue

            score = strength * 100

            result.append({
                "股票代號": stock,
                "強度": strength,
                "分數": score,
                "MA多頭": price["ma_up"],
                "突破": price["breakout"],
                "量增": price["vol_up"]
            })

        except:
            continue

    rank_df = pd.DataFrame(result)

    if rank_df.empty:
        st.error("沒有資料（欄位或資料來源問題）")
        st.stop()

    rank_df = rank_df.sort_values("分數", ascending=False)

    final_df = rank_df[rank_df["分數"] > rank_df["分數"].quantile(0.85)]

    st.success(f"完成：{len(final_df)} 檔")

    st.dataframe(final_df, use_container_width=True)
