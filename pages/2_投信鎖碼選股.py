import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V3.1", layout="wide")
st.title("投信鎖碼股篩選器 V3.1（完整技術版）")

# =========================
# TWSE 投信資料
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

# =========================
# 數字轉換
# =========================
def to_number(x):
    try:
        return int(str(x).replace(",", "").replace("+", "").strip())
    except:
        return 0

# =========================
# 抓歷史投信資料
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

        time.sleep(0.05)

    if len(all_data) == 0:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

# =========================
# Yahoo 股價
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):

    try:
        ticker = yf.Ticker(f"{stock}.TW")
        hist = ticker.history(period="6mo")

        if len(hist) < 60:
            return None

        close = hist["Close"]
        vol = hist["Volume"]

        last = close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]

        rise20 = (last / close.iloc[-20] - 1) * 100

        dist_ma20 = (last - ma20) / ma20 * 100
        dist_ma60 = (last - ma60) / ma60 * 100

        vol5 = vol.tail(5).mean()
        vol20 = vol.tail(20).mean()

        return {
            "收盤價": round(last, 2),
            "MA20": round(ma20, 2),
            "MA60": round(ma60, 2),
            "近20日漲幅%": round(rise20, 2),
            "距離月線%": round(dist_ma20, 2),
            "距離季線%": round(dist_ma60, 2),
            "5日均量": int(vol5),
            "20日均量": int(vol20)
        }

    except:
        return None

# =========================
# UI
# =========================
days = st.slider("回溯天數", 30, 90, 60)

if st.button("開始篩選"):

    with st.spinner("下載投信資料..."):
        df = load_data(days)

    if df.empty:
        st.error("無資料")
        st.stop()

    st.success(f"投信資料筆數：{len(df):,}")

    stock_col = "證券代號"

    buy_col = None
    name_col = None

    for c in df.columns:
        if "買賣超" in c:
            buy_col = c
        if "證券名稱" in c:
            name_col = c

    if buy_col is None:
        st.error("找不到買賣超欄位")
        st.stop()

    df[buy_col] = df[buy_col].apply(to_number)
    df["買超張數"] = df[buy_col] / 1000
    df["日期"] = pd.to_datetime(df["日期"])

    # 股票名稱
    name_map = {}
    if name_col:
        name_map = (
            df[[stock_col, name_col]]
            .drop_duplicates()
            .set_index(stock_col)[name_col]
            .to_dict()
        )

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
            "近20日買超張數": buy20,
            "近60日買超張數": buy60
        })

    rank_df = pd.DataFrame(result)

    # =========================
    # 技術面整合
    # =========================
    price_list = []

    progress = st.progress(0)

    for i, stock in enumerate(rank_df["股票代號"]):

        data = get_price(stock)

        if data:
            data["股票代號"] = stock
            price_list.append(data)

        progress.progress((i + 1) / len(rank_df))

    progress.empty()

    price_df = pd.DataFrame(price_list)

    rank_df = rank_df.merge(price_df, on="股票代號", how="left")

    rank_df["股票名稱"] = rank_df["股票代號"].map(name_map)

    # =========================
    # 篩選條件 V3.1
    # =========================
    rank_df = rank_df[
        (rank_df["投信連買天數"] >= 3) &
        (rank_df["投信連買天數"] <= 8) &
        (rank_df["近20日買超張數"] >= 1000) &
        (rank_df["近20日漲幅%"] < 12) &
        (rank_df["收盤價"] > rank_df["MA20"]) &
        (rank_df["MA20"] > rank_df["MA60"]) &
        (rank_df["距離月線%"] < 8) &
        (rank_df["5日均量"] < rank_df["20日均量"])
    ]

    # =========================
    # 分數
    # =========================
    rank_df["鎖碼分數"] = (
        rank_df["投信連買天數"] * 40 +
        rank_df["近20日買超張數"] * 0.01 -
        rank_df["近20日漲幅%"] * 3 -
        rank_df["距離月線%"] * 2
    )

    rank_df = rank_df.sort_values("鎖碼分數", ascending=False)

    # =========================
    # 顯示
    # =========================
    st.success(f"符合條件：{len(rank_df)} 檔")

    show_cols = [
        "股票代號",
        "股票名稱",
        "投信連買天數",
        "近20日買超張數",
        "收盤價",
        "MA20",
        "MA60",
        "距離月線%",
        "距離季線%",
        "近20日漲幅%",
        "鎖碼分數"
    ]

    st.dataframe(rank_df[show_cols], use_container_width=True)

    csv = rank_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "下載CSV",
        csv,
        "投信鎖碼V3_1.csv",
        "text/csv"
    )
