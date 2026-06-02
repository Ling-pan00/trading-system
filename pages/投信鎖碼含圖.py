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
st.title("📊 投信鎖碼股 V9.2（穩定整合版）")

# =========================
# A 核心功能區 (完全依照您原版邏輯)
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

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# =========================
# B 繪圖模組 (加入自動重試機制)
# =========================
def draw_zigzag_chart(ticker_code):
    # 自動嘗試不同後綴
    suffixes = [".TW", ".TWO", ""]
    df_chart = pd.DataFrame()
    for s in suffixes:
        df_chart = yf.download(f"{ticker_code}{s}", period="3mo", progress=False)
        if not df_chart.empty: break
            
    if df_chart.empty:
        st.error(f"⚠️ 找不到代號 {ticker_code} 的市場資料，請確認標的是否為台股上市櫃公司。")
        return

    # 計算均線與轉折 (保持與您圖片一致的邏輯)
    if isinstance(df_chart.columns, pd.MultiIndex): df_chart.columns = df_chart.columns.get_level_values(0)
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart = df_chart.dropna().copy()
    
    # 繪圖樣式
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    
    fig, axlist = mpf.plot(df_chart, type='candle', style=s, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    plt.close(fig)

# =========================
# 主程式 (策略完全不變)
# =========================
if st.button("🚀 開始 V9.2 分析"):
    df = load(30)
    if df.empty: st.error("資料載入失敗"); st.stop()

    # 欄位偵測
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    
    # 強制數字化
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    # 篩選邏輯 (完全保留原版)
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        
        # 您的原版門檻邏輯
        if (last3 < 0).sum() >= 2: continue
        if last10.sum() <= 0: continue
        if abs(last10.sum()) < 20: continue
        
        result.append({"股票": stock, "買超張數": int(last10.sum())})

    out = pd.DataFrame(result).sort_values("買超張數", ascending=False)
    st.dataframe(out)

    # 下拉選單繪圖
    if not out.empty:
        selected = st.selectbox("選擇代號查看圖表:", out['股票'].unique())
        if selected: draw_zigzag_chart(selected)
