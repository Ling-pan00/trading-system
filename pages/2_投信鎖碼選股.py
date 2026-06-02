import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.1", layout="wide")
st.title("投信鎖碼股 V9.1（防爆量修正版）")

# =========================
# TWSE 抓資料
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


# =========================
# 連續抓多日
# =========================
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

    if not all_df:
        return pd.DataFrame()

    df = pd.concat(all_df, ignore_index=True)

    # ⚠️ 保證時間排序正確
    df = df.sort_values(["證券代號", "date"])

    return df


# =========================
# 找欄位（防TWSE改版）
# =========================
def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None


# =========================
# 開始執行
# =========================
if st.button("開始 V9.1"):

    df = load(30)

    if df.empty:
        st.error("沒有抓到資料")
        st.stop()

    st.write("原始資料:", df.shape)

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])

    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗")
        st.stop()

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    # =========================
    # 🔥 鎖碼核心邏輯（修正版）
    # =========================
    for stock, g in df.groupby(stock_col):

        try:
            g = g.sort_values("date")

            series = g[buy_col].values

            if len(series) < 10:
                continue

            last3 = series[-3:]
            last10 = series[-10:]

            last3_sum = last3.sum()
            last10_sum = last10.sum()

            # =========================
            # ❌ 濾網1：連續買超（核心）
            # =========================
            if (last3 <= 0).any():
                continue

            # =========================
            # ❌ 濾網2：大方向必須偏多
            # =========================
            if last10_sum <= 0:
                continue

            # =========================
            # ❌ 濾網3：避免小單雜訊
            # =========================
            if abs(last10_sum) < 50:
                continue

            # =========================
            # ❌ 濾網4：至少要有「加碼趨勢」
            # =========================
            if last3_sum < (last10_sum / 3):
                continue

            strength = last3_sum / (abs(last10_sum) + 1)

            result.append({
                "股票": stock,
                "強度": round(strength, 4),
                "近3日買超": int(last3_sum),
                "近10日買超": int(last10_sum)
            })

        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.warning("目前沒有符合『鎖碼條件』的股票")
        st.stop()

    out = out.sort_values("強度", ascending=False)

    st.success(f"鎖碼完成：{len(out)} 檔（已去雜訊版）")

    st.dataframe(out)
