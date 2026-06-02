import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼 V9.2 整合版", layout="wide")
st.title("投信鎖碼 V9.2（精準選股 + 轉折圖表）")

# ==========================================
# 1. 投信選股核心 (保持你的原汁原味)
# ==========================================
def get_v92_data():
    all_df = []
    # 這裡抓取最近 30 天資料
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
    
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    
    # 欄位偵測與清理
    stock_col = [c for c in df.columns if '代號' in c][0]
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        last3, last10 = s[-3:], s[-10:]
        
        # 條件判斷
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    return pd.DataFrame(result).sort_values("強度", ascending=False)

# ==========================================
# 2. 轉折圖表模組 (整合你的專業轉折邏輯)
# ==========================================
def draw_zigzag_chart(ticker):
    # 自動補齊代號
    symbols = [f"{ticker}.TW", f"{ticker}.TWO"]
    df = pd.DataFrame()
    for s in symbols:
        data = yf.download(s, period="3mo", progress=False)
        if not data.empty and len(data) > 10:
            df = data
            break
            
    if df.empty:
        st.error("⚠️ 無法取得該股票的歷史交易數據")
        return

    # 計算均線
    df['5MA'] = df['Close'].rolling(5).mean()
    df['10MA'] = df['Close'].rolling(10).mean()
    df['20MA'] = df['Close'].rolling(20).mean()
    
    # 轉折標記邏輯
    h = (df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))
    b = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))
    
    # 繪圖
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df.index, df['Close'], color='black', alpha=0.3, label='Price')
    ax.plot(df.index, df['5MA'], color='orange', label='5MA')
    ax.scatter(df.index[h], df['High'][h], color='red', marker='v', label='H')
    ax.scatter(df.index[b], df['Low'][b], color='green', marker='^', label='B')
    
    ax.legend(); ax.grid(True)
    st.pyplot(fig)
    plt.close(fig)

# ==========================================
# 3. 執行介面
# ==========================================
if st.button("🚀 開始 V9.2 篩選"):
    st.session_state.data = get_v92_data()

if 'data' in st.session_state and not st.session_state.data.empty:
    st.success(f"成功篩選出 {len(st.session_state.data)} 檔股票")
    st.dataframe(st.session_state.data, use_container_width=True)
    
    target = st.selectbox("請選擇要看圖的股票:", st.session_state.data["股票"].astype(str).tolist())
    if st.button("繪製專業轉折圖"):
        draw_zigzag_chart(target)
elif 'data' in st.session_state:
    st.warning("目前沒有符合鎖碼條件的標的")
