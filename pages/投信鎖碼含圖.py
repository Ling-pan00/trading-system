import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼", layout="wide")
st.title("📊 投信鎖碼分析 (成功碼整合版)")

# =========================
# 您的原始成功邏輯 (完全保留)
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
# 繪圖功能 (獨立掛載，不會影響策略)
# =========================
def draw_chart(ticker):
    try:
        # 強制使用您的代號 + .TW
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"無法繪製 {ticker}，查無資料")
            return
        
        # 繪圖樣式
        fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖異常: {e}")

# =========================
# 主程式 (策略執行區)
# =========================
if st.button("🚀 執行投信鎖碼分析"):
    df = load(30)
    # 確保欄位名稱符合您原始的資料表頭 (請檢查證交所目前的實際表頭名稱)
    stock_col = "證券代號"
    buy_col = "買賣超"
    
    # 執行您的成功策略
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        
        last3, last10 = series[-3:], series[-10:]
        
        # 您堅持的篩選策略
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
