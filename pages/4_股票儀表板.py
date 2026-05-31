import streamlit as st
import pandas as pd

st.title("📊 2000檔台股專業選股系統")

# 假資料（未來換API）
from random import random, randint

def fake_data(t):
    return {
        "close": randint(50,200),
        "change_pct": random()*6,
        "volume": randint(1000,5000),
        "avg_volume": 3000,
        "ma5": 100,
        "ma20": 95
    }

universe = ["2330.TW","2317.TW","2454.TW","2303.TW"]

results = []

for t in universe:

    d = fake_data(t)

    stock = {
        "ticker": t,
        "close": d["close"],
        "change_pct": d["change_pct"],
        "volume": d["volume"],
        "avg_volume": d["avg_volume"],
        "ma5": d["ma5"],
        "ma20": d["ma20"],
        "trend_up": d["ma5"] > d["ma20"],
        "breakout": d["close"] > d["ma20"],
        "sector": classify_sector(t)
    }

    stock["score"] = score(stock)

    results.append(stock)

df = pd.DataFrame(results)

mode, N = market_regime(results)

df = df.sort_values("score", ascending=False)

top = df.head(N)

st.subheader("📌 市場狀態")
st.write(mode)

st.subheader("📊 族群強弱")
st.write(df.groupby("sector")["score"].mean())

st.subheader("🥇 Top 股票")
st.dataframe(top)
