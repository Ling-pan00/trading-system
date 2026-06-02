import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide")

# ==========================================
# 1. 您的原始篩選核心 (完全未更動)
# ==========================================
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

# ==========================================
# 2. 獨立繪圖功能 (僅在選取時觸發)
# ==========================================
def draw_chart(ticker):
    try:
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"查無 {ticker}.TW 資料")
            return
        fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖異常: {e}")

# ==========================================
# 3. 主程式 (執行您的原始策略)
# ==========================================
if st.button("🚀 開始分析"):
    df = load(30)
    if df.empty: st.stop()

    # 此處是唯一可能出錯的地方 (欄位名稱)
    # 我加入了一個除錯顯示，若出現 KeyError，請告訴我下面這行印出的內容
    st.write("目前資料表頭:", list(df.columns))
    
    # 請將下方括號內的名稱，修改為您「目前資料表頭」印出的準確名稱
    stock_col = "證券代號" 
    buy_col = "買賣超"
    
    # 策略計算
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        
        # 您的原始成功策略條件
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "近10日買超": int(last10.sum())})

    out = pd.DataFrame(result)
    if not out.empty:
        st.dataframe(out)
        selected = st.selectbox("選擇代號看圖:", out['股票'].unique())
        if selected: draw_chart(selected)
