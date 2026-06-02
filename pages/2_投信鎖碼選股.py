import streamlit as st
import pandas as pd
import requests
import time
import re
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V6.2", layout="wide")
st.title("投信鎖碼股 V6.2（修正單位穩定版）")

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

        if "data" not in data or "fields" not in data:
            return pd.DataFrame()

        return pd.DataFrame(data["data"], columns=data["fields"])

    except:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_data(days=60):
    all_data = []
    today = datetime.today()

    checked = 0
    i = 0

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

        if h is None or h.empty or len(h) < 30:
            return None

        close = h["Close"]
        vol = h["Volume"]

        price = float(close.iloc[-1])
        ma20 = float(close.rolling(20).mean().iloc[-1])

        ma_up = ma20 > float(close.rolling(20).mean().iloc[-5])

        breakout = price > float(close.rolling(20).max().iloc[-2])

        vol_break = False
        if len(vol) >= 20:
            vol_break = vol.iloc[-1] > vol.tail(20).mean() * 1.3

        return {
            "price": price,
            "ma20": ma20,
            "ma_up": ma_up,
            "breakout": breakout,
            "vol_break": vol_break
        }

    except:
        return None


# =========================
# UI
# =========================
days = st.slider("回溯天數", 40, 100, 60)

if st.button("開始 V6.2 鎖碼篩選"):

    df = load_data(days)

    st.write("原始資料筆數:", df.shape)

    if df.empty:
        st.error("TWSE 無資料")
        st.stop()

    # =========================
    # columns
    # =========================
    stock_col = find_col(df, ["證券代號", "代號"])
    buy_col = find_col(df, ["買賣超", "買超", "賣超"])
    name_col = find_col(df, ["證券名稱", "名稱"])

    st.write("stock_col:", stock_col)
    st.write("buy_col:", buy_col)

    df = df.dropna(subset=[stock_col])

    # 🔥 修正重點：不要再 /1000（TWSE本來就是股數）
    df["買超張數"] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    name_map = {}
    if name_col:
        name_map = df[[stock_col, name_col]].drop_duplicates().set_index(stock_col)[name_col].to_dict()

    result = []

    # =========================
    # analysis
    # =========================
    for stock, g in df.groupby(stock_col):

        try:
            if is_etf(stock):
                continue

            g = g.sort_index()

            last3 = g["買超張數"].tail(3).sum()
            last5 = g["買超張數"].tail(5).sum()
            last10 = g["買超張數"].tail(10).sum()
            last20 = g["買超張數"].tail(20).sum()

            # 🔥 正確強度（不平均到死）
            inst_strength = (last3 + last5 + last10) / 3

            price = get_price(stock)
            if price is None:
                continue

            score = (
                inst_strength * 0.0005 +   # 🔥 股數太大 → 改縮放
                last20 * 0.0002 +
                (1 if price["ma_up"] else 0) * 10 +
                (1 if price["breakout"] else 0) * 15 +
                (1 if price["vol_break"] else 0) * 10
            )

            # =========================
            # 🔥 V6.2 鎖碼條件（合理版）
            # =========================
            if not (
                last10 > 20000 and
                inst_strength > 5000 and
                score > 15 and
                (price["ma_up"] or price["breakout"])
            ):
                continue

            result.append({
                "股票代號": stock,
                "名稱": name_map.get(stock, ""),
                "連買強度": round(inst_strength),
                "近20買超": round(last20),
                "收盤": price["price"],
                "MA20": price["ma20"],
                "突破": price["breakout"],
                "量增": price["vol_break"],
                "分數": round(score, 2)
            })

        except:
            continue

    rank_df = pd.DataFrame(result)

    if rank_df.empty:
        st.error("沒有鎖碼股（條件仍可再放寬）")
        st.stop()

    rank_df = rank_df.sort_values("分數", ascending=False)

    st.success(f"鎖碼完成：{len(rank_df)} 檔（正常 20～120 檔）")

    st.dataframe(rank_df, use_container_width=True)

    st.download_button(
        "下載CSV",
        rank_df.to_csv(index=False).encode("utf-8-sig"),
        "v62_lock.csv",
        "text/csv"
    )
