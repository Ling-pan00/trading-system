import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.3-lite", layout="wide")
st.title("投信鎖碼股 V9.3-lite（穩定不空版）")

# =========================
# TWSE 投信資料
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
# 外資資料
# =========================
def get_foreign(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT38U?date={date}&response=json"
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
# 抓資料
# =========================
def load(days=30):
    inst = []
    foreign = []
    today = datetime.today()

    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")

        df1 = get_day(d)
        df2 = get_foreign(d)

        if df1 is not None and not df1.empty:
            inst.append(df1)
        if df2 is not None and not df2.empty:
            foreign.append(df2)

        time.sleep(0.02)

        if len(inst) >= days:
            break

    inst_df = pd.concat(inst, ignore_index=True) if inst else pd.DataFrame()
    foreign_df = pd.concat(foreign, ignore_index=True) if foreign else pd.DataFrame()

    return inst_df, foreign_df


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
# 主程式
# =========================
if st.button("開始 V9.3-lite"):

    inst_df, foreign_df = load(30)

    if inst_df.empty:
        st.error("投信資料不足")
        st.stop()

    stock_col = find(inst_df, ["證券代號"])
    buy_col = find(inst_df, ["買賣超"])

    inst_df[buy_col] = pd.to_numeric(inst_df[buy_col], errors="coerce").fillna(0)

    # =========================
    # 外資整理（安全版）
    # =========================
    foreign_map = {}
    if not foreign_df.empty:
        f_stock = find(foreign_df, ["證券代號"])
        f_buy = find(foreign_df, ["買賣超"])

        foreign_df[f_buy] = pd.to_numeric(foreign_df[f_buy], errors="coerce").fillna(0)

        for stock, g in foreign_df.groupby(f_stock):
            g = g.sort_values("date")
            foreign_map[stock] = g[f_buy].tail(10).sum()

    result = []

    # =========================
    # 鎖碼核心
    # =========================
    for stock, g in inst_df.groupby(stock_col):

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
            # ✔ 條件1：允許輕微洗盤
            # =========================
            if (last3 < 0).sum() >= 2:
                continue

            # =========================
            # ✔ 條件2：投信方向要偏多
            # =========================
            if last10_sum <= 5:
                continue

            # =========================
            # ✔ 條件3：去雜訊（放寬）
            # =========================
            if abs(last10_sum) < 10:
                continue

            # =========================
            # ✔ 條件4：外資「不能大賣」（放寬版）
            # =========================
            foreign_sum = foreign_map.get(stock, 0)

            if foreign_sum < -120:   # 放寬，避免誤殺
                continue

            # =========================
            # ✔ 穩定度 & 強度
            # =========================
            stability = last10_sum / (abs(last3_sum) + 1)
            strength = last3_sum / (abs(last10_sum) + 1)

            result.append({
                "股票": stock,
                "強度": round(strength, 4),
                "穩定度": round(stability, 4),
                "投信10日": int(last10_sum),
                "外資10日": int(foreign_sum)
            })

        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.warning("目前市場偏整理，無明顯鎖碼股（正常）")
        st.stop()

    out = out.sort_values("強度", ascending=False)

    st.success(f"完成：{len(out)} 檔（穩定版）")
    st.dataframe(out)
