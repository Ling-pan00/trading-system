import streamlit as st
import pandas as pd
import json

# =========================
# 假資料（之後可換成真實API）
# =========================

def get_data():
    return pd.DataFrame([
        {
            "ticker": "2330",
            "change_pct": 4,
            "volume": 20000,
            "avg_volume_5d": 15000,
            "close": 900,
            "ma5": 880,
            "ma20": 860,
            "breakout": True,
            "upper_shadow": False,
            "trend_up": True,
            "red_3": False
        },
        {
            "ticker": "2454",
            "change_pct": 6,
            "volume": 18000,
            "avg_volume_5d": 15000,
            "close": 120,
            "ma5": 115,
            "ma20": 110,
            "breakout": False,
            "upper_shadow": False,
            "trend_up": True,
            "red_3": False
        },
        {
            "ticker": "3017",
            "change_pct": 2,
            "volume": 9000,
            "avg_volume_5d": 8000,
            "close": 45,
            "ma5": 44,
            "ma20": 43,
            "breakout": False,
            "upper_shadow": False,
            "trend_up": True,
            "red_3": False
        }
    ])


# =========================
# 風控
# =========================

def risk_filter(s):

    if s["change_pct"] >= 8:
        return False

    if s["volume"] > s["avg_volume_5d"] * 2 and s["upper_shadow"]:
        return False

    return True


# =========================
# 打分
# =========================

def score(s):

    sc = 0

    if 3 <= s["change_pct"] < 5:
        sc += 1
    elif 5 <= s["change_pct"] < 8:
        sc += 2

    if s["volume"] > s["avg_volume_5d"]:
        sc += 1

    if s["close"] > s["ma5"]:
        sc += 1

    if s["close"] > s["ma20"]:
        sc += 1

    if s["breakout"]:
        sc += 1

    if not s["upper_shadow"]:
        sc += 1

    if s["trend_up"]:
        sc += 1

    if s["red_3"]:
        sc -= 2

    return sc


# =========================
# 市場判斷
# =========================

def market_decision(df):

    strong = len(df[df["score"] >= 7])

    if strong >= 2:
        return "可做"
    elif strong == 1:
        return "小倉"
    else:
        return "不做"


# =========================
# 主程式
# =========================

st.set_page_config(page_title="交易系統", layout="wide")

st.title("📊 每日交易系統")

df = get_data()

candidates = []

for _, s in df.iterrows():

    s = s.to_dict()

    if not risk_filter(s):
        continue

    s["score"] = score(s)
    candidates.append(s)

result = pd.DataFrame(candidates)

if len(result) == 0:
    st.warning("今日無符合標的")
    st.stop()

result = result.sort_values("score", ascending=False)

top10 = result.head(10)

decision = market_decision(top10)

# =========================
# UI
# =========================

st.subheader("📌 市場判斷")
st.write(decision)

st.subheader("🥇 Top 1")
st.write(top10.iloc[0]["ticker"])

st.subheader("📈 Top 10")
st.dataframe(top10[["ticker","score"]])

st.subheader("🚨 風控規則")
st.write("""
- +8% 不追
- 爆量長上影淘汰
- 連3紅K降分
""")
