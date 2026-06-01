import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import mplfinance as mpf

# 設定頁面與佈局
st.set_page_config(page_title="全量強勢突破選股", layout="wide")

# 1. 股票清單函式
@st.cache_data
def get_industry_stock_pool():
    # 這裡放您的 565 檔清單
    return ["1503.TW", "1504.TW", "2330.TW", "2454.TW", "3008.TW"] # 完整版請填入您的完整 List

# --- 頁面頂端：日期與筆數 ---
st.title("📊 565 檔強勢帶量突破選股系統")

# 使用容器確保上方資訊區完整渲染
with st.container():
    col1, col2 = st.columns([1, 1])
    
    with col1:
        days = st.slider("歷史計算天數", 30, 365, 120)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
    
    with col2:
        stock_pool = get_industry_stock_pool()
        st.metric("總監控檔數", f"{len(stock_pool)} 檔")
        st.write(f"資料區間: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

st.divider()

# --- 選擇區 ---
selected_ticker = st.selectbox("請選擇要查看的股票代號", stock_pool)

# --- 繪圖區 ---
def draw_chart(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['10MA'] = df['Close'].rolling(window=10).mean()
    
    # 修正 mplfinance 繪圖風格
    mc = mpf.make_marketcolors(up='red', down='green', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', facecolor='#FFFFFF')
    
    apds = [
        mpf.make_addplot(df['5MA'], color='orange', width=1.5),
        mpf.make_addplot(df['10MA'], color='blue', width=1.5)
    ]
    
    fig, ax = mpf.plot(df, type='candle', style=s, addplot=apds, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)

# 執行分析
if st.button("查看走勢圖"):
    with st.spinner('正在從 Yahoo Finance 下載資料...'):
        df = yf.download(selected_ticker, start=start_date, end=end_date)
        if not df.empty:
            draw_chart(df)
        else:
            st.error("無法取得該檔股票資料，請檢查代號是否正確。")
