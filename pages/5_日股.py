import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 系統設定
st.set_page_config(page_title="金融技術分析繪圖", layout="wide")
st.title("📈 金融技術分析圖表產生器")

# 1. 輸入與標的設定
ticker_input = st.text_input("請輸入股票代號 (例如 4099.JP, 6787.JP, 6227.JP):", "4099.JP")

# 數據下載 (抓取近 180 天)
@st.cache_data
def load_data(ticker):
    end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    return yf.download(ticker, start=start_date, end=end_date)

if ticker_input:
    df = load_data(ticker_input)
    
    if not df.empty:
        # 資料清理
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        
        # 顯示 MA 數值資訊 (仿照您提供的圖片樣式)
        now_5, now_10, now_20 = df['5MA'].iloc[-1], df['10MA'].iloc[-1], df['20MA'].iloc[-1]
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
            <h4 style="margin:0;">{ticker_input} 技術指標</h4>
            <span style="color: #FF9800;"><b>5MA: {now_5:.2f}</b></span> | 
            <span style="color: #2196F3;"><b>10MA: {now_10:.2f}</b></span> | 
            <span style="color: #9C27B0;"><b>20MA: {now_20:.2f}</b></span>
        </div>
        """, unsafe_allow_html=True)

        # 繪圖設定 (仿照您提供的圖片風格)
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=True)
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=1.5),
            mpf.make_addplot(df['10MA'], color='blue', width=1.5),
            mpf.make_addplot(df['20MA'], color='purple', width=1.5)
        ]
        
        # 產生圖表
        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=ap, 
            returnfig=True, figsize=(12, 7), 
            volume=True, panel_ratios=(3, 1),
            title=f"\n{ticker_input} Daily Chart"
        )
        
        st.pyplot(fig)
    else:
        st.error("無法取得該代號的資料，請確認輸入格式是否正確（例如包含 .JP）。")
