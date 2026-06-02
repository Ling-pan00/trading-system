import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V5.1", layout="wide")
st.title("投信鎖碼股篩選器 V5.1（穩定打分版）")

# =========================
# TWSE資料
# =========================
@st.cache_data(ttl=3600)
def get_day_data(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date_str}&response=json"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if "data" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["日期"] = date_str
        return df

    except:
        return pd.DataFrame()

def to_number(x):
    try:
        return int(str(x).replace(",", "").replace("+", "").strip())
    except:
        return 0

# =========================
# 抓資料
# =========================
@st.cache_data(ttl=3600)
def load_data(days=60):
    all_data = []
    today = datetime.today()

    for i in range(days):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y%m%d")

        df = get_day_data(date_str)

        if not df.empty:
            all_data.append(df)

        time.sleep(0.02)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

# =========================
# 股價
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):
    try:
        t = yf.Ticker(f"{stock}.TW")
        hist = t.history(period="6mo")

        if hist is None or hist.empty:
            return None

        close = hist["Close"]
        vol = hist["Volume"]

        if len(close) < 60:
            return None

        price = close.iloc[-1]

        ma20 = close.rolling(20).mean().iloc[-1]
        ma20_prev = close.rolling(20).mean().iloc[-5]

        ma20_up = ma20 > ma20_prev

        high20 = close.rolling(20).max().iloc[-2]

        breakout = price > high20

        vol_break = vol.iloc[-1] > vol.tail(20).mean() * 1.5

        fake_break = (
            vol.iloc[-1] > vol.tail(10).mean() * 2.5
            and (price / close.iloc[-2] - 1) > 0.05
        )

        return {
            "收盤價": price,
            "MA20": ma20,
            "MA60": close.rolling(60).mean().iloc[-1],
            "MA20上升": ma20_up,
            "突破": breakout and vol_break,
            "假突破": fake_break
        }

    except:
        return None

# =========================
# UI
# =========================
days = st.slider("回溯天數", 40, 100, 60)
min_keep = st.slider("最少保留檔數", 5, 50, 20)

if st.button("開始 V5.1 篩選"):

    df = load_data(days)

    if df.empty:
        st.error("無資料")
        st.stop()

    stock_col = "證券代號"

    buy_col = [c for c in df.columns if "買賣超" in c][0]
    name_col = [c for c in df.columns if "證券名稱" in c]
    name_col = name_col[0] if name_col else None

    df[buy_col] = df[buy_col].apply(to_number)
    df["買超張數"] = df[buy_col] / 1000
    df["日期"] = pd.to_datetime(df["日期"])

    name_map = {}
    if name_col:
        name_map = (
            df[[stock_col, name_col]]
            .drop_duplicates()
            .set_index(stock_col)[name_col]
            .to_dict()
        )

    result = []

    # =========================
    # 核心計算（打分模型）
    # =========================
    for stock, g in df.groupby(stock_col):

        g = g.sort_values("日期")

        # 投信強度（3天 vs 10天）
        last10 = g.tail(10)["買超張數"].sum()
        last3 = g.tail(3)["買超張數"].sum()

        inst_strength = (last3 / 3) - (last10 / 10)

        buy20 = g.tail(20)["買超張數"].sum()

        price_data = get_price(stock)

        if price_data is None:
            continue

        if price_data["假突破"]:
            fake_penalty = -50
        else:
            fake_penalty = 0

        breakout_score = 1 if price_data["突破"] else 0
        ma_up_score = 1 if price_data["MA20上升"] else 0

        # =========================
        # 🔥 打分（核心）
        # =========================
        score = (
            inst_strength * 40 +
            buy20 * 0.02 +
            breakout_score * 50 +
            ma_up_score * 20 +
            fake_penalty
        )

        # 只排除極弱
        if price_data["收盤價"] <= price_data["MA20"]:
            continue

        result.append({
            "股票代號": stock,
            "股票名稱": name_map.get(stock, ""),
            "投信強度": inst_strength,
            "近20買超": buy20,
            "收盤價": price_data["收盤價"],
            "MA20": price_data["MA20"],
            "MA60": price_data["MA60"],
            "突破": breakout_score,
            "MA20上升": ma_up_score,
            "分數": score
        })

    rank_df = pd.DataFrame(result)

    if rank_df.empty:
        st.error("沒有結果（請再放寬回溯天數或市場條件）")
        st.stop()

    rank_df = rank_df.sort_values("分數", ascending=False)

    # 防呆保底
    if len(rank_df) < min_keep:
        st.warning("結果太少 → 自動補足")
        rank_df = rank_df.head(min_keep)

    st.success(f"V5.1 結果：{len(rank_df)} 檔")

    st.dataframe(rank_df, use_container_width=True)

    csv = rank_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "下載CSV",
        csv,
        "投信鎖碼V5_1.csv",
        "text/csv"
    )
