import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import yfinance as yf

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V4", layout="wide")
st.title("投信鎖碼股篩選器 V4（法人級強化版）")

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
def load_data(days=80):
    all_data = []
    today = datetime.today()

    for i in range(days):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y%m%d")

        df = get_day_data(date_str)

        if not df.empty:
            all_data.append(df)

        time.sleep(0.03)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

# =========================
# 股價
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):
    try:
        ticker = yf.Ticker(f"{stock}.TW")
        hist = ticker.history(period="8mo")

        if hist.empty or len(hist) < 40:
            return None

        close = hist["Close"]
        vol = hist["Volume"]

        last = close.iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]

        rise20 = (last / close.iloc[-20] - 1) * 100 if len(close) > 20 else 0

        return {
            "收盤價": round(last, 2),
            "MA20": round(ma20, 2),
            "MA60": round(ma60, 2),
            "近20日漲幅%": round(rise20, 2),
            "距離月線%": round((last - ma20) / ma20 * 100, 2),
            "距離季線%": round((last - ma60) / ma60 * 100, 2),
            "5日均量": int(vol.tail(5).mean()),
            "20日均量": int(vol.tail(20).mean()) if len(vol) >= 20 else 0
        }

    except:
        return None

# =========================
# UI
# =========================
days = st.slider("回溯天數", 30, 120, 80)

if st.button("開始篩選 V4"):

    df = load_data(days)

    if df.empty:
        st.error("無資料")
        st.stop()

    stock_col = "證券代號"

    buy_col = [c for c in df.columns if "買賣超" in c]
    name_col = [c for c in df.columns if "證券名稱" in c]

    if not buy_col:
        st.error("找不到買賣超欄位")
        st.stop()

    buy_col = buy_col[0]
    name_col = name_col[0] if name_col else None

    df[buy_col] = df[buy_col].apply(to_number)
    df["買超張數"] = df[buy_col] / 1000
    df["日期"] = pd.to_datetime(df["日期"])

    # =========================
    # 股票名稱
    # =========================
    name_map = {}
    if name_col:
        name_map = df[[stock_col, name_col]].drop_duplicates().set_index(stock_col)[name_col].to_dict()

    result = []

    # =========================
    # 籌碼計算
    # =========================
    for stock, g in df.groupby(stock_col):

        g = g.sort_values("日期")

        buy_series = g["買超張數"].values

        # 🔥 連買（改成更穩定）
        streak = 0
        for v in reversed(buy_series):
            if v > 0:
                streak += 1
            else:
                break

        buy20 = g.tail(20)["買超張數"].sum()
        buy60 = g.tail(60)["買超張數"].sum()

        # 🔥 加速度（近5日 vs 前15日）
        recent5 = g.tail(5)["買超張數"].sum()
        prev15 = g.tail(20).head(15)["買超張數"].sum()
        accel = recent5 - (prev15 / 3)

        result.append({
            "股票代號": stock,
            "投信連買天數": streak,
            "近20日買超張數": buy20,
            "近60日買超張數": buy60,
            "買超加速度": accel
        })

    rank_df = pd.DataFrame(result)

    # =========================
    # 技術面補充
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
    # V4：改成「寬進嚴出」
    # =========================
    filtered = rank_df.copy()

    filtered = filtered[
        (filtered["投信連買天數"] >= 2) &
        (filtered["近20日買超張數"] >= 200) &
        (filtered["近20日漲幅%"] < 25)
    ]

    # =========================
    # 分數系統（核心）
    # =========================
    filtered["鎖碼分數"] = (
        filtered["投信連買天數"] * 25 +
        filtered["近20日買超張數"] * 0.02 +
        filtered["買超加速度"] * 0.5 -
        filtered["近20日漲幅%"] * 1.5 +
        filtered["距離月線%"] * -1
    )

    filtered = filtered.sort_values("鎖碼分數", ascending=False)

    # =========================
    # 顯示
    # =========================
    st.success(f"V4符合：{len(filtered)} 檔")

    cols = [
        "股票代號",
        "股票名稱",
        "投信連買天數",
        "近20日買超張數",
        "買超加速度",
        "收盤價",
        "MA20",
        "MA60",
        "近20日漲幅%",
        "距離月線%",
        "鎖碼分數"
    ]

    st.dataframe(filtered[cols], use_container_width=True)

    csv = filtered.to_csv(index=False).encode("utf-8-sig")

    st.download_button("下載CSV", csv, "投信鎖碼V4.csv", "text/csv")
