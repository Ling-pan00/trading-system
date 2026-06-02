import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V5.3", layout="wide")
st.title("投信鎖碼股 V5.3（穩定工程版）")

# =========================
# TWSE
# =========================
@st.cache_data(ttl=3600)
def get_day_data(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date_str}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if "data" not in data:
            return pd.DataFrame()

        return pd.DataFrame(data["data"], columns=data["fields"])

    except:
        return pd.DataFrame()

def to_number(x):
    try:
        return int(str(x).replace(",", "").replace("+", "").strip())
    except:
        return 0

@st.cache_data(ttl=3600)
def load_data(days=60):
    all_data = []
    today = datetime.today()

    for i in range(days):
        d = today - timedelta(days=i)
        df = get_day_data(d.strftime("%Y%m%d"))

        if not df.empty:
            all_data.append(df)

        time.sleep(0.02)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

# =========================
# ETF判斷
# =========================
def is_etf(code):
    code = str(code)
    return code.startswith("00")

# =========================
# 股價（失敗不淘汰）
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

        price = close.iloc[-1]

        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20

        ma20_up = ma20 > close.rolling(20).mean().iloc[-5] if len(close) >= 25 else False

        high20 = close.rolling(20).max().iloc[-2] if len(close) >= 20 else price

        breakout = price > high20

        vol_break = vol.iloc[-1] > vol.tail(20).mean() * 1.3 if len(vol) >= 20 else False

        return {
            "price": price,
            "ma20": ma20,
            "ma60": ma60,
            "ma_up": ma20_up,
            "breakout": breakout,
            "vol_break": vol_break
        }

    except:
        return None

# =========================
# UI
# =========================
days = st.slider("回溯天數", 40, 100, 60)

if st.button("開始 V5.3"):

    df = load_data(days)

    if df.empty:
        st.error("TWSE 無資料")
        st.stop()

    stock_col = "證券代號"
    buy_col = [c for c in df.columns if "買賣超" in c][0]
    name_col = [c for c in df.columns if "證券名稱" in c]
    name_col = name_col[0] if name_col else None

    df[buy_col] = df[buy_col].apply(to_number)
    df["買超張數"] = df[buy_col] / 1000

    name_map = {}
    if name_col:
        name_map = df[[stock_col, name_col]].drop_duplicates().set_index(stock_col)[name_col].to_dict()

    result = []

    for stock, g in df.groupby(stock_col):

        # 🔥 剔除ETF
        if is_etf(stock):
            continue

        g = g.sort_values("日期")

        last3 = g.tail(3)["買超張數"].sum()
        last10 = g.tail(10)["買超張數"].sum()

        inst_strength = (last3 / 3) - (last10 / 10)
        buy20 = g.tail(20)["買超張數"].sum()

        price_data = get_price(stock)

        # 🔥 沒資料也不淘汰（給0）
        if price_data is None:
            price_data = {
                "price": 0,
                "ma20": 0,
                "ma60": 0,
                "ma_up": 0,
                "breakout": 0,
                "vol_break": 0
            }

        # =========================
        # 🔥 打分模型（核心）
        # =========================
        score = (
            inst_strength * 50 +
            buy20 * 0.02 +
            price_data["ma_up"] * 10 +
            price_data["breakout"] * 20 +
            price_data["vol_break"] * 10
        )

        result.append({
            "股票代號": stock,
            "股票名稱": name_map.get(stock, ""),
            "投信強度": inst_strength,
            "近20買超": buy20,
            "收盤價": price_data["price"],
            "MA20": price_data["ma20"],
            "MA60": price_data["ma60"],
            "MA20上升": price_data["ma_up"],
            "突破": price_data["breakout"],
            "量能突破": price_data["vol_break"],
            "分數": score
        })

    rank_df = pd.DataFrame(result)

    if rank_df.empty:
        st.error("沒有結果（請增加回溯天數）")
        st.stop()

    rank_df = rank_df.sort_values("分數", ascending=False)

    st.success(f"V5.3 完成：{len(rank_df)} 檔")

    st.dataframe(rank_df, use_container_width=True)

    st.download_button(
        "下載CSV",
        rank_df.to_csv(index=False).encode("utf-8-sig"),
        "v53_final.csv",
        "text/csv"
    )
