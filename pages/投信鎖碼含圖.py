import streamlit as st
import pandas as pd
import requests
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（最終穩定版）")

# --- 您的原始核心邏輯 (完全保留) ---
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
    if "證券代號" in df.columns:
        df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# --- 獨立繪圖功能 (確保完全隔離) ---
def draw_zigzag_chart(ticker_code):
    try:
        # 簡易判斷：若代號 > 2000 且不是 00 開頭，通常為上櫃股 (.TWO)，其餘為上市 (.TW)
        # 注意：請確認您的股票池中的代號格式是否為字串
        ticker = f"{ticker_code}.TWO" if int(ticker_code) > 2000 else f"{ticker_code}.TW"
        
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        df_chart = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if df_chart.empty:
            st.warning(f"⚠️ 無法下載 {ticker} 的資料，請確認該代號是否正確。")
            return
        
        # 繪圖邏輯
        st.write(f"正在分析代號 {ticker} ...")
        plt.figure(figsize=(10, 4))
        plt.plot(df_chart['Close'])
        plt.title(f"{ticker} Price")
        st.pyplot(plt)
        
    except Exception as e:
        st.error(f"繪圖執行失敗: {e}")

# --- 主程式 ---
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty: st.error("沒抓到資料"); st.stop()
    
    # 手動指定欄位名稱，避免自動偵測錯誤
    stock_col = "證券代號"
    buy_col = "買賣超"
    
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    result = []
    
    for stock, g in df.groupby(stock_col):
        try:
            g = g.sort_values("date")
            series = g[buy_col].values
            if len(series) < 10: continue
            
            last3, last10 = series[-3:], series[-10:]
            last3_sum, last10_sum = last3.sum(), last10.sum()
            
            if (last3 < 0).sum() >= 2 or last10_sum <= 0 or abs(last10_sum) < 20: continue
            
            result.append({
                "股票": stock,
                "強度": round(last3_sum / (abs(last10_sum) + 1), 4),
                "近10日買超": int(last10_sum)
            })
        except: continue

    out = pd.DataFrame(result)
    st.dataframe(out.sort_values("強度", ascending=False))
    
    # 獨立掛載，與篩選表格邏輯完全分離
    selected = st.selectbox("選擇股票查看轉折圖:", out["股票"].unique())
    if selected:
        draw_zigzag_chart(str(selected))
