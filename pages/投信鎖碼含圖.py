import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V9.2 強力篩選版", layout="wide")

# --- 繪圖邏輯 (改為簡潔 K 線) ---
def plot_stock(ticker):
    ticker_str = str(ticker).strip()
    # 嘗試抓取 TW/TWO
    for suffix in ['.TW', '.TWO']:
        df = yf.download(f"{ticker_str}{suffix}", period="3mo", progress=False)
        if not df.empty and len(df) > 10: break
    
    if df.empty: return

    # 繪圖：移除不必要的軸，只看 K 線
    fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(8, 4))
    st.pyplot(fig)
    plt.close(fig)

# --- 選股邏輯 ---
if st.button("🚀 開始強力篩選"):
    # ... (載入數據邏輯保持不變) ...
    # 修正篩選邏輯：增加更嚴格的門檻
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        # 【更嚴格條件】：加強對「零散買盤」的排除
        if s[-3:].sum() < 50: continue # 近3日買超必須大於 50 張
        if (s[-3:] < 0).sum() > 0: continue # 近3日嚴禁有負值
        
        result.append({"股票": stock, "強度": round(s[-3:].sum()/100, 2)})

    st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.rerun()

# --- 顯示 ---
if not st.session_state.final_out.empty:
    df_show = st.session_state.final_out
    # 限制顯示前 20 檔，避免過多雜訊
    selected_stock = st.selectbox("選擇股票:", df_show["股票"].head(20).tolist())
    plot_stock(selected_stock)
    st.dataframe(df_show)
