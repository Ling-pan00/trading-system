import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼 V9.2", layout="wide")
st.title("📊 投信鎖碼股 V9.2 (最終穩定版)")

# =========================
# A. 資料載入區 (原始邏輯)
# =========================
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

# =========================
# B. 繪圖區 (加入強制後綴)
# =========================
def draw_chart(ticker):
    try:
        # 強制加入 .TW 進行下載
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"找不到 {ticker}.TW 的資料")
            return
        
        # 繪圖樣式
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        fig, ax = mpf.plot(df, type='candle', style=s, returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"無法繪圖: {e}")

# =========================
# C. 主程式 (核心策略邏輯)
# =========================
if st.button("🚀 開始 V9.2 分析"):
    raw_df = load(30)
    if raw_df.empty: st.error("無資料"); st.stop()

    # 安全地清理買賣超欄位 (處理逗號)
    raw_df["買賣超"] = pd.to_numeric(raw_df["買賣超"].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in raw_df.groupby("證券代號"):
        g = g.sort_values("date")
        series = g["買賣超"].values
        if len(series) < 10: continue
        
        # 這是您最原始的策略門檻
        last3, last10 = series[-3:], series[-10:]
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "近10日買超": int(last10.sum())})

    out = pd.DataFrame(result)
    
    if not out.empty:
        st.dataframe(out)
        selected = st.selectbox("請選擇代號查看圖表:", out['股票'].unique())
        if selected:
            draw_chart(selected)
    else:
        st.warning("目前市場無符合條件股票")
