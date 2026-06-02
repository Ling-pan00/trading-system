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

# --- 1. 您的原始核心邏輯 (完全保留) ---
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

# --- 2. 獨立的繪圖函數 (僅在點選時執行) ---
def draw_chart(ticker):
    try:
        # 嘗試下載台股資料
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"無法繪製 {ticker}，查無資料")
            return
        
        # 繪圖樣式設定
        fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖發生錯誤: {e}")

# --- 3. 執行主程式 ---
if st.button("🚀 開始分析"):
    df = load(30)
    if df.empty: st.error("資料載入失敗"); st.stop()
    
    # 強制指定欄位名稱為您原版使用的名稱，徹底解決 KeyError
    # 若錯誤仍發生，請檢查此處名稱是否與證交所實際回傳的欄位完全一致
    stock_col = "證券代號"
    buy_col = "買賣超"
    
    # 執行與您原版完全一致的數字處理
    try:
        df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    except KeyError:
        st.error(f"發生 KeyError，找不到欄位: {buy_col}。請確認證交所原始資料表頭。")
        st.stop()
    
    result = []
    # 篩選邏輯完全依照您的原始條件
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        
        last3, last10 = series[-3:], series[-10:]
        
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "近10日買超": int(last10.sum())})

    out = pd.DataFrame(result)
    
    if not out.empty:
        st.success(f"完成：{len(out)} 檔")
        st.dataframe(out)
        selected = st.selectbox("請選擇代號查看圖表:", out['股票'].unique())
        if selected:
            draw_chart(selected)
    else:
        st.warning("未篩選出符合條件的股票")
