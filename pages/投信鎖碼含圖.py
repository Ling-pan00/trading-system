import streamlit as st
import pandas as pd
import requests
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ==========================================================
# 1. 您的原始篩選策略 (完全保留)
# ==========================================================
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
        time.sleep(0.02)
        if len(all_df) >= days: break
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    if "證券代號" in df.columns: df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# ==========================================================
# 2. 獨立繪圖函式 (專門解決無法抓取資料的問題)
# ==========================================================
def draw_chart(stock_id):
    # 自動補上 .TW 或 .TWO，這是 yfinance 的強制規定
    try:
        code_str = str(stock_id).strip()
        ticker = f"{code_str}.TW" if int(code_str) < 2000 else f"{code_str}.TWO"
        
        # 抓取最近 3 個月資料
        df = yf.download(ticker, period="3mo", progress=False)
        
        if df.empty:
            st.error(f"⚠️ 無法取得 {stock_id} ({ticker}) 的數據，請檢查代號。")
            return

        # 確保所有數據為數值，防止繪圖崩潰
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()

        # 繪圖
        fig, ax = mpf.plot(df, type='candle', volume=True, returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖發生錯誤: {e}")

# ==========================================================
# 3. 整合執行
# ==========================================================
st.title("投信鎖碼股 V9.2 (已修正繪圖串接)")

if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    
    out = pd.DataFrame(result)
    st.dataframe(out)

    # 串接：透過 selectbox 傳遞代號給 draw_chart，徹底隔絕資料污染
    if not out.empty:
        selected_stock = st.selectbox("選擇股票看轉折圖:", out['股票'].unique())
        if selected_stock:
            draw_chart(selected_stock)
    else:
        st.warning("目前無符合條件之標的。")
