import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（平衡實戰版）")

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
# 多日載入
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

    # 保證排序正確
    if "證券代號" in df.columns:
        df = df.sort_values(["證券代號", "date"])

    return df


# =========================
# 欄位偵測
# =========================
def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None


# =========================
# 開始
# =========================
if st.button("開始 V9.2"):

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
    # 🔥 鎖碼核心（平衡版）
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
            # ✔ 條件1：允許短期洗盤（最多1天負）
            # =========================
            if (last3 < 0).sum() >= 2:
                continue

            # =========================
            # ✔ 條件2：中期方向仍偏多
            # =========================
            if last10_sum <= 0:
                continue

            # =========================
            # ✔ 條件3：避免太小雜訊
            # =========================
            if abs(last10_sum) < 20:
                continue

            # =========================
            # ✔ 穩定度（避免亂飆）
            # =========================
            stability = last10_sum / (abs(last3_sum) + 1)

            # =========================
            # ✔ 強度（鎖碼核心）
            # =========================
            strength = last3_sum / (abs(last10_sum) + 1)

            result.append({
                "股票": stock,
                "強度": round(strength, 4),
                "穩定度": round(stability, 4),
                "近3日買超": int(last3_sum),
                "近10日買超": int(last10_sum)
            })

        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.warning("目前市場沒有明顯投信鎖碼（偏整理盤）")
        st.stop()

    out = out.sort_values("強度", ascending=False)

    st.success(f"完成：{len(out)} 檔（平衡鎖碼版）")

    st.dataframe(out)
