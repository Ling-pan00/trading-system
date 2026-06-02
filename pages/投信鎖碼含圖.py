import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import numpy as np

# ==========================================
# 1. 轉折 K 線圖繪製模組 (你確認成功的版本)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()

    df_chart['Close'] = pd.to_numeric(df_chart['Close'], errors='coerce')
    df_chart['High'] = pd.to_numeric(df_chart['High'], errors='coerce')
    df_chart['Low'] = pd.to_numeric(df_chart['Low'], errors='coerce')
    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()

    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()

    zigzag_points = []
    grouped = df_chart.groupby('State_Group')
    group_ids = sorted(df_chart['State_Group'].unique())

    for g_id in group_ids:
        group_data = grouped.get_group(g_id)
        state = group_data['State'].iloc[0]
        if g_id <= 2: continue
        if state == 1:
            highest_idx = group_data['High'].idxmax()
            zigzag_points.append((df_chart.index.get_loc(highest_idx), df_chart.loc[highest_idx, 'High']))
            df_chart.loc[highest_idx, 'Label'] = "H"
        else:
            lowest_idx = group_data['Low'].idxmin()
            zigzag_points.append((df_chart.index.get_loc(lowest_idx), df_chart.loc[lowest_idx, 'Low']))
            df_chart.loc[lowest_idx, 'Label'] = "B"

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df_chart[['5MA', '10MA', '20MA']]) ]

    fig, axlist = mpf.plot(df_chart, type='candle', style=s_style, addplot=plots, returnfig=True, figsize=(12, 6), volume=True)
    main_ax = axlist[0]
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points)
        main_ax.plot(x, y, color='black', alpha=0.5, linewidth=1.5)

    st.pyplot(fig)
    plt.close(fig)

# ==========================================
# 2. 投信鎖碼邏輯與介面
# ==========================================
st.set_page_config(layout="wide")
st.title("投信鎖碼股 V9.2（最終整合版）")

# 初始化 session_state
if 'out_df' not in st.session_state:
    st.session_state.out_df = pd.DataFrame()

if st.button("開始 V9.2"):
    # 這裡放入你原本的 load 和 for 迴圈篩選邏輯
    # 篩選完後，請將結果賦值給 st.session_state.out_df
    # 例如:
    # df_result = pd.DataFrame(result)
    # st.session_state.out_df = df_result
    st.rerun()

# 確保讀取資料時不會發生 NameError
if not st.session_state.out_df.empty:
    col1, col2 = st.columns([1, 3])
    with col1:
        selected_stock = st.selectbox("請選擇股票:", st.session_state.out_df['股票'].unique())
    with col2:
        draw_zigzag_chart(f"{selected_stock}.TW", selected_stock)
else:
    st.info("請按下按鈕進行篩選。")
