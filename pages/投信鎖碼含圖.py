import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼 V9.2 穩定版", layout="wide")
st.title("投信鎖碼 V9.2（極限穩定版）")

# --- 1. 選股與數據核心 (你的 V9.2 規則) ---
def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 2. 專業繪圖 (使用 matplotlib 解決 ValueError) ---
def plot_technical_chart(ticker):
    ticker_str = str(ticker).strip()
    # 抓取資料
    df = yf.download(f"{ticker_str}.TW", period="3mo", progress=False)
    if df.empty: df = yf.download(f"{ticker_str}.TWO", period="3mo", progress=False)
    if df.empty: return

    # 計算均線
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # 顯示上方數值面板
    cols = st.columns(3)
    for i, ma in enumerate(['MA5', 'MA10', 'MA20']):
        val = df[ma].iloc[-1]
        prev = df[ma].iloc[-2]
        trend = "▲" if val > prev else "▼"
        cols[i].metric(ma, f"{val:.2f}", trend)

    # 繪圖
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df['Close'], label='Close', color='black', alpha=0.5)
    ax.plot(df.index, df['MA5'], label='5MA', color='orange')
    ax.plot(df.index, df['MA10'], label='10MA', color='blue')
    ax.plot(df.index, df['MA20'], label='20MA', color='purple')
    
    ax.set_title(f"{ticker} 技術走勢")
    ax.legend()
    ax.grid(True)
    st.pyplot(fig)
    plt.close(fig)

# --- 3. 選股邏輯區 ---
if st.button("開始 V9.2"):
    df = load(30)
    # 動態抓取欄位
    stock_col = [c for c in df.columns if '代號' in c][0]
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        # 【你的原始篩選條件】
        last3, last10 = s[-3:], s[-10:]
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    
    st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.rerun()

# --- 4. 結果顯示 ---
if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    st.success(f"篩選出 {len(st.session_state.final_out)} 檔")
    selected = st.selectbox("選擇股票:", st.session_state.final_out["股票"].tolist())
    plot_technical_chart(selected)
    st.dataframe(st.session_state.final_out)
