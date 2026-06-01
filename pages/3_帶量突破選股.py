import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf

# 設定頁面配置
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統 (無依賴版本)")

@st.cache_data
def get_industry_stock_pool():
    # 565 檔股票清單 (已精簡顯示，實際使用您的完整列表)
    return ["1503.TW", "1504.TW", "2330.TW", "2454.TW", "3008.TW", "2317.TW"] # 請在此處放回您的完整 565 檔

def draw_zigzag_chart(df, ticker):
    """使用您原本熟悉的轉折邏輯 (Pandas/Numpy)"""
    # 計算均線
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['10MA'] = df['Close'].rolling(window=10).mean()
    df['20MA'] = df['Close'].rolling(window=20).mean()
    
    # 轉折波段邏輯
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

    zigzag_points = []
    df['Label'] = np.nan
    grouped = df.groupby('State_Group')
    
    for g_id, group_data in grouped:
        if len(group_data) < 2: continue
        state = group_data['State'].iloc[0]
        if state == 1:
            idx = group_data['High'].idxmax()
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
            df.loc[idx, 'Label'] = "H"
        else:
            idx = group_data['Low'].idxmin()
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))
            df.loc[idx, 'Label'] = "B"

    # 繪圖
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    
    fig, axlist = mpf.plot(df, type='candle', style=s_style, returnfig=True, figsize=(10, 5), volume=False)
    main_ax = axlist[0]
    
    if len(zigzag_points) > 1:
        x_c, y_c = zip(*zigzag_points)
        main_ax.plot(x_c, y_c, color='black', alpha=0.5, linewidth=1.5)
        
    st.pyplot(fig)
    plt.close(fig)

# 掃描核心
total_pool = get_industry_stock_pool()
if st.button("⚡ 啟動掃描", type="primary"):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    with st.spinner("正在掃描中..."):
        # 批次下載
        data = yf.download(tickers=total_pool, start=start_date, end=end_date, group_by='ticker', progress=False)
        
        for t in total_pool:
            df = data[t] if len(total_pool) > 1 else data
            if df.empty or len(df) < 22: continue
            
            # 策略：突破20日新高 + 量增
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            
            if df['Close'].iloc[-1] > high_20 and df['Volume'].iloc[-1] > (vol_avg_20 * 2):
                st.subheader(f"✅ 發現突破：{t}")
                draw_zigzag_chart(df, t)

st.success("掃描完畢！")
