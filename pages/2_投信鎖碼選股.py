import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 Signal版", layout="wide")
st.title("投信鎖碼股 V9.3（訊號 + 進場區間 + 集中度）")

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
# 抓資料
# =========================
def load(days=40):
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
# 訊號判斷
# =========================
def signal_class(last3_sum, last10_sum):
    momentum = last3_sum / (abs(last10_sum) + 1)

    if last10_sum > 50 and last3_sum > 20:
        return "🔥 現在可以買"
    elif last10_sum > 0 and momentum < 0.3:
        return "🟡 等回檔"
    else:
        return "🔴 已過追價點"


# =========================
# 集中度（proxy）
# =========================
def concentration(series):
    if len(series) < 10:
        return 0
    last3 = abs(series[-3:].sum())
    last10 = abs(series[-10:].sum())
    return round(last3 / (last10 + 1), 3)


# =========================
# 主程式
# =========================
if st.button("開始分析"):

    df = load(40)

    if df.empty:
        st.error("沒有資料")
        st.stop()

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])

    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗，請檢查 TWSE 回傳")
        st.write(df.columns.tolist())
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
        # 基本鎖碼濾網（不會太嚴）
        # =========================
        if last10 <= -20:
            continue

        if last3 < -10:
            continue

        # =========================
        # 指標
        # =========================
        strength = last3 / (abs(last10) + 1)
        conc = concentration(series)
        sig = signal_class(last3, last10)

        # =========================
        # 投信成本區（推估）
        # =========================
        avg_cost_proxy = round(last10 / 10, 2)

        result.append({
            "股票": stock,
            "訊號": sig,
            "強度": round(strength, 4),
            "集中度": conc,
            "投信10日": int(last10),
            "近3日": int(last3),
            "成本區(推估)": avg_cost_proxy
        })

    out = pd.DataFrame(result)

    if out.empty:
        st.warning("目前沒有明顯投信鎖碼股")
        st.stop()

    # 排序
    out = out.sort_values(["訊號", "強度"], ascending=[True, False])

    st.success(f"完成：{len(out)} 檔（訊號版）")
    st.dataframe(out)
