import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# --- 選股邏輯：隔離區 ---
def get_v92_result():
    all_df = []
    # 嚴格控制只抓取需要的日期，避免資料冗餘
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
    
    df = pd.concat(all_df)
    stock_col = [c for c in df.columns if '代號' in c][0]
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    
    # 這裡確保數值處理無誤，排除字串干擾
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    results = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        last3, last10 = s[-3:], s[-10:]
        # 【嚴格執行你的條件】
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        results.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    return pd.DataFrame(results).sort_values("強度", ascending=False)

# --- 繪圖邏輯：極簡穩定版 ---
def plot_simple(ticker):
    df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
    if df.empty: df = yf.download(f"{ticker}.TWO", period="3mo", progress=False)
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df['Close'], color='black')
    st.pyplot(fig)

# --- 執行與顯示 ---
if st.button("開始 V9.2"):
    st.session_state.out = get_v92_result()
    st.rerun()

if 'out' in st.session_state:
    st.write(f"當前篩選出 {len(st.session_state.out)} 檔")
    st.dataframe(st.session_state.out)
    sel = st.selectbox("選股:", st.session_state.out["股票"].tolist())
    plot_simple(sel)
