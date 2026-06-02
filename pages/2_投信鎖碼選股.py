import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time

# =========================
# Page
# =========================
st.set_page_config(page_title="投信鎖碼股 V8 TWSE版", layout="wide")
st.title("投信鎖碼股 V8（TWSE穩定版）")

# =========================
# TWSE API（正確用法）
# =========================
@st.cache_data(ttl=3600)
def get_twse(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date_str}&response=json"

    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if data.get("stat") != "OK":
            return pd.DataFrame()

        if "data" not in data or "fields" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["data"], columns=data["fields"])
        return df

    except:
        return pd.DataFrame()


# =========================
# 拉多日資料
# =========================
@st.cache_data(ttl=3600)
def load(days=30):
    all_df = []
    today = datetime.today()

    for i in range(days * 2):  # 避開假日
        d = today - timedelta(days=i)
        df = get_twse(d.strftime("%Y%m%d"))

        if not df.empty:
            all_df.append(df)

        time.sleep(0.02)

        if len(all_df) >= days:
            break

    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()


# =========================
# 欄位抓取
# =========================
def find_col(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None


# =========================
# price
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):
    try:
        h = yf.Ticker(f"{stock}.TW").history(period="6mo")
        if h.empty:
            return None

        close = h["Close"]

        return {
            "price": float(close.iloc[-1]),
            "ma20": float(close.rolling(20).mean().iloc[-1]),
            "breakout": close.iloc[-1] > close.rolling(20).max().iloc[-2]
        }

    except:
        return None


# =========================
# UI
# =========================
days = st.slider("回溯天數", 10, 60, 30)

if st.button("開始分析"):

    df = load(days)

    st.write("資料筆數:", df.shape)

    if df.empty:
        st.error("TWSE 沒回資料（可能是假日或API限制）")
        st.stop()

    st.write("欄位:", df.columns.tolist())

    stock_col = find_col(df, ["證券代號"])
    buy_col = find_col(df, ["買賣超"])

    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗")
        st.stop()

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    # =========================
    # 逐檔分析（修正：不用錯誤groupby強依賴）
    # =========================
    for stock in df[stock_col].unique():

        try:
            g = df[df[stock_col] == stock]

            if str(stock).startswith("00"):
                continue

            last10 = g[buy_col].tail(10).sum()
            last20 = g[buy_col].tail(20).sum()

            if last20 == 0:
                continue

            strength = last10 / (abs(last20) + 1)

            price = get_price(stock)
            if price is None:
                continue

            score = strength * 100

            result.append({
                "股票": stock,
                "投信動能": last10,
                "強度": strength,
                "收盤": price["price"],
                "MA20": price["ma20"],
                "突破": price["breakout"],
                "分數": score
            })

        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.error("沒有符合條件股票（但資料是正常的）")
        st.stop()

    out = out.sort_values("分數", ascending=False)

    st.success(f"完成：{len(out)} 檔")

    st.dataframe(out, use_container_width=True)

    st.download_button(
        "下載CSV",
        out.to_csv(index=False).encode("utf-8-sig"),
        "twse_v8.csv",
        "text/csv"
    )
