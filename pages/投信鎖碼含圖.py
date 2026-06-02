import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide")
st.title("V9.2 回歸原始版本")

# 1. 原始載入邏輯
def load_data():
    all_df = []
    for i in range(30):
        d = (datetime.today() - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.02)
    return pd.concat(all_df) if all_df else pd.DataFrame()

# 2. 原始選股核心 (不做任何篩選以外的動作)
def run_strategy(df):
    stock_col = [c for c in df.columns if '代號' in c][0]
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    
    # 簡單且明確的處理
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        last3, last10 = s[-3:], s[-10:]
        # 這是你原本的 4 個判斷條件，完全保留
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    return pd.DataFrame(result).sort_values("強度", ascending=False)

# 3. 極簡版繪圖 (只畫重點，保證不崩潰)
def plot_chart(ticker):
    df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
    if df.empty: df = yf.download(f"{ticker}.TWO", period="3mo", progress=False)
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df['Close'], label='Price', color='black')
    ax.legend()
    st.pyplot(fig)

# 執行區
if st.button("開始 V9.2"):
    df = load_data()
    st.session_state.out = run_strategy(df)
    st.rerun()

if 'out' in st.session_state:
    st.dataframe(st.session_state.out)
    sel = st.selectbox("選股:", st.session_state.out["股票"].tolist())
    plot_chart(sel)
