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
st.set_page_config(page_title="投信鎖碼股 V5.7", layout="wide")
st.title("投信鎖碼股 V5.7（保證有輸出版）")

# =========================
# TWSE 抓資料
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


def to_number(x):
    try:
        s = str(x)
        s = re.sub(r"[^\d\-]", "", s)
        if s in ["", "-"]:
            return 0
        return int(s)
    except:
        return 0


@st.cache_data(ttl=3600)
def load_data(days=60):
    all_data = []
    today = datetime.today()

    checked = 0
    i = 0

    while checked < days and i < 120:
        d = today - timedelta(days=i)
        i += 1

        df = get_day_data(d.strftime("%Y%m%d"))

        if df is not None and not df.empty:
            all_data.append(df)
            checked += 1

        time.sleep(0.03)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)


# =========================
# 欄位偵測（加強版）
# =========================
def find_col(df, keywords):
    if df is None or df.empty:
        return None

    for c in df.columns:
        for k in keywords:
            if k in str(c):
                return c
    return None


# =========================
# ETF
# =========================
def is_etf(code):
    try:
        return str(code).startswith("00")
    except:
        return False


# =========================
# 股價
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):
    try:
        t = yf.Ticker(f"{stock}.TW")
        hist = t.history(period="6mo")

        if hist is None or hist.empty or len(hist) < 20:
            return None

        close = hist["Close"]
        vol = hist["Volume"]

        price = float(close.iloc[-1])
        ma20 = float(close.rolling(20).mean().iloc[-1])

        ma20_prev = float(close.rolling(20).mean().iloc[-5]) if len(close) > 25 else ma20
        ma_up = ma20 > ma20_prev

        high20 = float(close.rolling(20).max().iloc[-2]) if len(close) >= 20 else price
        breakout = price > high20

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

if st.button("開始 V5.7 篩選"):

    df = load_data(days)

    st.write("📊 原始資料筆數:", df.shape)

    if df is None or df.empty:
        st.error("TWSE 無資料")
        st.stop()

    # =========================
    # 欄位抓取
    # =========================
    stock_col = find_col(df, ["證券代號", "代號"])
    buy_col = find_col(df, ["買賣超", "買超", "賣超"])
    name_col = find_col(df, ["證券名稱", "名稱"])

    st.write("stock_col:", stock_col)
    st.write("buy_col:", buy_col)

    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗")
        st.write(df.columns)
        st.stop()

    # =========================
    # 清理資料
    # =========================
    df = df.dropna(subset=[stock_col])

    df[buy_col] = df[buy_col].apply(to_number)
    df["買超張數"] = df[buy_col] / 1000

    name_map = {}
    if name_col:
        name_map = df[[stock_col, name_col]].drop_duplicates().set_index(stock_col)[name_col].to_dict()

    result = []

    # =========================
    # 主迴圈
    # =========================
    for stock, g in df.groupby(stock_col):

        try:
            if is_etf(stock):
                continue

            if g.empty:
                continue

            if "日期" in g.columns:
                g = g.sort_values("日期")

            last3 = g.tail(3)["買超張數"].sum() if len(g) >= 3 else 0
            last10 = g.tail(10)["買超張數"].sum() if len(g) >= 10 else 0
            buy20 = g.tail(20)["買超張數"].sum()

            inst_strength = (last3 / 3) - (last10 / 10)

            price_data = get_price(stock)

            if price_data is None:
                price_data = {
                    "price": 0,
                    "ma20": 0,
                    "ma_up": False,
                    "breakout": False,
                    "vol_break": False
                }

            # 🔥 分數放大（關鍵修正）
            score = (
                inst_strength * 300 +
                buy20 * 0.05 +
                (1 if price_data["ma_up"] else 0) * 10 +
                (1 if price_data["breakout"] else 0) * 20 +
                (1 if price_data["vol_break"] else 0) * 10
            )

            result.append({
                "股票代號": stock,
                "股票名稱": name_map.get(stock, ""),
                "投信強度": inst_strength,
                "近20買超(千股)": buy20,
                "收盤價": price_data["price"],
                "MA20": price_data["ma20"],
                "MA20上升": price_data["ma_up"],
                "突破": price_data["breakout"],
                "量能突破": price_data["vol_break"],
                "分數": score
            })

        except:
            continue

    rank_df = pd.DataFrame(result)

    if rank_df.empty:
        st.error("沒有結果（條件太嚴或資料不足）")
        st.stop()

    rank_df = rank_df.sort_values("分數", ascending=False)

    st.success(f"完成：{len(rank_df)} 檔股票")

    st.dataframe(rank_df, use_container_width=True)

    st.download_button(
        "下載CSV",
        rank_df.to_csv(index=False).encode("utf-8-sig"),
        "v57.csv",
        "text/csv"
    )
