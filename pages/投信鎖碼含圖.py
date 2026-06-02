import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# --- 您的成功核心 (完全保留，沒有動任何邏輯) ---
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

# --- 繪圖函數 (獨立掛載) ---
def draw_chart(ticker):
    try:
        # 強制用 .TW，這是不影響篩選策略的純顯示功能
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"代號 {ticker}.TW 無市場資料")
            return
        fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖發生錯誤: {e}")

# --- 主程式 (您的原始篩選邏輯) ---
if st.button("🚀 開始分析"):
    df = load(30)
    
    # 這裡直接使用您原版成功使用的名稱
    stock_col = "證券代號"
    buy_col = "買賣超"
    
    # 執行與您原版完全一致的數字轉換
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        
        last3, last10 = series[-3:], series[-10:]
        
        # 篩選條件完全未動
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "近10日買超": int(last10.sum())})

    out = pd.DataFrame(result)
    
    if not out.empty:
        st.dataframe(out)
        selected = st.selectbox("選擇代號查看圖表:", out['股票'].unique())
        if selected:
            draw_chart(selected)
    else:
        st.warning("未篩選出符合條件的股票")
