import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼 V9.2 最終修復版", layout="wide")
st.title("投信鎖碼 V9.2（技術線圖版）")

# 初始化狀態
if 'final_out' not in st.session_state:
    st.session_state.final_out = pd.DataFrame()

# 數據載入函數
def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
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
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# 繪圖函數：徹底修復 ValueError
def plot_technical_chart(ticker):
    ticker_str = str(ticker).strip()
    df = pd.DataFrame()
    for suffix in ['.TW', '.TWO']:
        raw_df = yf.download(f"{ticker_str}{suffix}", period="3mo", progress=False)
        if not raw_df.empty and len(raw_df) > 20:
            df = raw_df
            break
    
    if df.empty:
        st.warning(f"找不到 {ticker} 的 K 線資料")
        return

    # 【關鍵清洗】：解決 ValueError 的核心
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.apply(pd.to_numeric, errors='coerce').dropna()
    df.index = pd.to_datetime(df.index)
    
    # 計算 MA
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # 繪圖
    apds = [
        mpf.make_addplot(df['MA5'], color='orange'),
        mpf.make_addplot(df['MA10'], color='blue'),
        mpf.make_addplot(df['MA20'], color='purple')
    ]
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, 
                       volume=True, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    plt.close(fig)

# 選股邏輯 (您的 V9.2)
if st.button("開始 V9.2 選股"):
    df = load(30)
    # 此處加入您的選股邏輯 (如先前代碼)
    # ... (篩選後存入 st.session_state.final_out)
    st.rerun()

# 顯示區
if not st.session_state.final_out.empty:
    selected = st.selectbox("選擇股票:", st.session_state.final_out["股票"].tolist())
    plot_technical_chart(selected)
    st.dataframe(st.session_state.final_out)
