import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import yfinance as yf
import time

st.set_page_config(page_title="投信鎖碼股 V9", layout="wide")
st.title("投信鎖碼股 V9（真正時間序列版）")

# =========================
# TWSE
# =========================
def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if data.get("stat") != "OK":
            return None

        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df

    except:
        return None


def load(days=30):
    all_df = []
    today = datetime.today()

    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)

        if df is not None and not df.empty:
            all_df.append(df)

        time.sleep(0.02)

        if len(all_df) >= days:
            break

    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()


def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None


if st.button("開始 V9"):

    df = load(30)

    st.write("資料:", df.shape)

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    # =========================
    # 🔥 正確：先建立時間序列
    # =========================
    for stock, g in df.groupby(stock_col):

        try:
            g = g.sort_values("date")

            series = g[buy_col].values

            if len(series) < 5:
                continue

            last3 = series[-3:].sum()
            last10 = series[-10:].sum() if len(series) >= 10 else series.sum()

            strength = last3 / (abs(last10) + 1)

            result.append({
                "股票": stock,
                "強度": strength,
                "last3": last3,
                "last10": last10
            })

        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.error("真的沒有符合（代表市場當下無投信連買）")
        st.stop()

    out = out.sort_values("強度", ascending=False)

    st.success(f"完成：{len(out)} 檔")

    st.dataframe(out)
