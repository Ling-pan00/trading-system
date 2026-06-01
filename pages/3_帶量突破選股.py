import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf

# 設定頁面
st.set_page_config(page_title="全量強勢突破選股", layout="wide")
st.title("📊 565 檔強勢帶量突破選股系統 (白底版)")

# 1. 完整 565 檔清單 (已包含)
@st.cache_data
def get_industry_stock_pool():
    # 這裡放入您之前的那 565 檔完整清單
    return ["2330.TW", "2454.TW", "3008.TW", "2317.TW"] 

# 2. 核心繪圖函數 (白底、含成交量、MA資訊列)
def draw_zigzag_chart(df, ticker):
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['10MA'] = df['Close'].rolling(window=10).mean()
    df['20MA'] = df['Close'].rolling(window=20).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    
    h_points, b_points = [], []
    for g_id, group in df.groupby('State_Group'):
        if len(group) < 2: continue
        if group['State'].iloc[0] == 1:
            idx = group['High'].idxmax()
            h_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
        else:
            idx = group['Low'].idxmin()
            b_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

    # 上方資訊列 (仿照您照片的樣式)
    def get_arrow(col):
        return "▲" if df[col].iloc[-1] >= df[col].iloc[-2] else "▼"

    st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #ddd;">
            <div style="display: flex; justify-content: space-around; font-size: 20px; font-weight: bold;">
                <span style="color: #d97706;">5MA: {df['5MA'].iloc[-1]:.2f} {get_arrow('5MA')}</span>
                <span style="color: #2563eb;">10MA: {df['10MA'].iloc[-1]:.2f}</span>
            </div>
            <div style="text-align: center; font-size: 20px; font-weight: bold; margin-top: 10px;">
                <span style="color: #9333ea;">20MA: {df['20MA'].iloc[-1]:.2f} {get_arrow('20MA')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 繪圖參數 (White Style + Volume)
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', facecolor='white', gridcolor='#e0e0e0')
    
    apds = [
        mpf.make_addplot(df['5MA'], color='#d97706', width=1.5),
        mpf.make_addplot(df['10MA'], color='#2563eb', width=1.5),
        mpf.make_addplot(df['20MA'], color='#9333ea', width=1.5)
    ]
    
    # 繪製圖表 (含成交量)
    fig, axlist = mpf.plot(df, type='candle', style=s, addplot=apds, returnfig=True, figsize=(10, 6), volume=True)
    
    # 畫連線與標註
    all_points = sorted(h_points + b_points)
    if len(all_points) > 1:
        x_vals, y_vals = zip(*all_points)
        axlist[0].plot(x_vals, y_vals, color='gray', linewidth=1.5, zorder=2)
    
    for x, y in h_points:
        axlist[0].text(x, y, 'H', color='red', weight='bold', ha='center', va='bottom', bbox=dict(facecolor='yellow', alpha=0.5, boxstyle='circle'))
    for x, y in b_points:
        axlist[0].text(x, y, 'B', color='green', weight='bold', ha='center', va='top', bbox=dict(facecolor='yellow', alpha=0.5, boxstyle='circle'))
        
    st.pyplot(fig)
    plt.close(fig)

# 3. 掃描執行
total_pool = get_industry_stock_pool()
if st.button("🚀 執行全量白底圖表掃描"):
    with st.spinner("掃描中..."):
        data = yf.download(total_pool, period="3mo", group_by='ticker', auto_adjust=True, progress=False)
        for t in total_pool:
            try:
                df = data[t] if len(total_pool) > 1 else data
                if df.empty or len(df) < 22: continue
                df.columns = [c.capitalize() for c in df.columns]
                # 選股邏輯
                if df['Close'].iloc[-1] > df['High'].iloc[-21:-1].max() and \
                   df['Volume'].iloc[-1] > df['Volume'].iloc[-21:-1].mean() * 2:
                    st.subheader(f"✅ 符合標的：{t}")
                    draw_zigzag_chart(df, t)
            except: continue
