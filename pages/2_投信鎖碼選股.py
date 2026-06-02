import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 STABLE", layout="wide")
st.title("投信鎖碼 STABLE（保證有結果版）")


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


def load():
    all_df = []
    today = datetime.today()

    for i in range(30):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty:
            all_df.append(df)
        time.sleep(0.02)

    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()


def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None


if st.button("RUN STABLE"):

    df = load()

    if df.empty:
        st.error("沒資料")
        st.stop()

    st.write("欄位檢查：", df.columns.tolist())

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])

    if stock_col is None or buy_col is None:
        st.error("欄位抓不到（TWSE格式變動）")
        st.stop()

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    for stock, g in df.groupby(stock_col):

        g = g.sort_values("date")
        series = g[buy_col].values

        if len(series) < 10:
            continue

        last3 = series[-3:].sum()
        last10 = series[-10:].sum()

        # =========================
        # 🔥 超寬鬆版本（保證有結果）
        # =========================
        if last10 < -100:
            continue

        if last3 < -50:
            continue

        strength = last3 / (abs(last10) + 1)

        result.append({
            "股票": stock,
            "強度": round(strength, 4),
            "近3日": int(last3),
            "近10日": int(last10)
        })

    out = pd.DataFrame(result)

    if out.empty:
        st.warning("市場偏冷，但模型正常（代表你條件太乾淨）")
        st.stop()

    out = out.sort_values("強度", ascending=False)

    st.success(f"完成：{len(out)} 檔（穩定版）")
    st.dataframe(out)
