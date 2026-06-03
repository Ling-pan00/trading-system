import streamlit as st
import pandas as pd
import twstock
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（實戰穩定版）")

# =========================
# 核心函數：轉折點計算
# =========================
def get_zigzag_points(df):
    points = []
    if 'Close' not in df.columns: return points
    data = df['Close'].values
    for i in range(1, len(data) - 1):
        if data[i] > data[i-1] and data[i] > data[i+1]:
            points.append((df.index[i], data[i], 'H'))
        elif data[i] < data[i-1] and data[i] < data[i+1]:
            points.append((df.index[i], data[i], 'L'))
    return points

# =========================
# 改用 twstock 抓取歷史資料 (雲端更穩定)
# =========================
@st.cache_data(ttl=3600)
def get_twstock_data(sid):
    try:
        stock = twstock.Stock(str(sid))
        data = stock.fetch_3mo() 
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.set_index('date')
            df.columns = ['Capacity', 'Turnover', 'Open', 'High', 'Low', 'Close', 'Change', 'Transaction']
            for col in ['Open', 'High', 'Low', 'Close']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
    except:
        return pd.DataFrame()
    return pd.DataFrame()

# =========================
# 選股邏輯 (同你的原始需求)
# =========================
if st.button("開始 V9.2"):
    # 這裡放入你原有的 load 與篩選邏輯
    # ... (略) ...
    # 確保最後將結果存入 st.session_state['final_out']
    st.session_state['final_out'] = out 

# =========================
# 轉折圖分析 (直接從 final_out 讀取)
# =========================
if 'final_out' in st.session_state:
    st.write("---")
    st.subheader("🎯 轉折監測器")
    final_out = st.session_state['final_out']
    
    # 確保選取的是字串代號
    options = final_out["股票"].astype(str).tolist()
    sel = st.selectbox("分析個股：", options)
    
    df_k = get_twstock_data(sel)
    
    if not df_k.empty:
        df_k['5MA'] = df_k['Close'].rolling(5).mean()
        df_k['10MA'] = df_k['Close'].rolling(10).mean()
        df_k['20MA'] = df_k['Close'].rolling(20).mean()
        
        # 繪圖
        fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                               addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
        st.pyplot(fig)
    else:
        st.error(f"無法取得 {sel} 的歷史資料，請確認該代號是否正確。")
