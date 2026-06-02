import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# --- 您的原始篩選核心 (完全未更動) ---
def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except: return None

def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty: all_df.append(df)
        time.sleep(0.05)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 獨立繪圖函數 (新增功能) ---
def draw_chart(ticker):
    try:
        # 強制補上 .TW 避免找不到資料，這是繪圖唯一目的
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"代號 {ticker}.TW 無資料")
            return
        fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖異常: {e}")

# --- 主程式 ---
if st.button("🚀 開始分析"):
    df = load(30)
    # 強制指定您原版的欄位名稱，不做任何偵測
    stock_col = "證券代號"
    buy_col = "買賣超"
    
    # 執行與您原版完全一致的數字轉換 (這一步是您篩選檔數正確的關鍵)
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    # 篩選邏輯完全依照您的原始條件 (這一段我直接複製您的)
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        
        # 篩選門檻完全未動
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "近10日買超": int(last10.sum())})

    out = pd.DataFrame(result)
    
    if not out.empty:
        st.dataframe(out)
        # 下拉選單獨立執行繪圖
        selected = st.selectbox("選擇代號看圖:", out['股票'].unique())
        if selected: draw_chart(selected)
