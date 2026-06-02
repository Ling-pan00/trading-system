import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（最終實戰版）")

# --- 1. 狀態持久化設定 ---
if 'out_df' not in st.session_state:
    st.session_state.out_df = pd.DataFrame()

# --- 2. 您的成功繪圖模組 ---
def draw_zigzag_chart(ticker_code, stock_name):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name} 的數據。")
        return

    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna().copy()
    
    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()
    
    zigzag_points = []
    grouped = df_chart.groupby('State_Group')
    for g_id in sorted(df_chart['State_Group'].unique()):
        if g_id <= 2: continue
        group_data = grouped.get_group(g_id)
        if group_data['State'].iloc[0] == 1:
            h_idx = group_data['High'].idxmax()
            zigzag_points.append((df_chart.index.get_loc(h_idx), df_chart.loc[h_idx, 'High']))
            df_chart.loc[h_idx, 'Label'] = "H"
        else:
            b_idx = group_data['Low'].idxmin()
            zigzag_points.append((df_chart.index.get_loc(b_idx), df_chart.loc[b_idx, 'Low']))
            df_chart.loc[b_idx, 'Label'] = "B"

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df_chart[['5MA', '10MA', '20MA']])]
    fig, axlist = mpf.plot(df_chart, type='candle', style=s_style, addplot=plots, returnfig=True, figsize=(12, 6))
    
    main_ax = axlist[0]
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points)
        main_ax.plot(x, y, color='black', alpha=0.5, linewidth=1.5)
    
    st.pyplot(fig)
    plt.close(fig)

# --- 3. 選股邏輯 ---
def run_selection():
    # 此處保留您原本的 load 與篩選邏輯
    # 務必確保執行後回傳一個 DataFrame (欄位需包含 '股票')
    # 以下為您的結構示範：
    # ... (您的 load() 與 groupby 篩選邏輯) ...
    return out # 返回 DataFrame

# --- 4. 介面執行 ---
if st.button("開始 V9.2"):
    with st.spinner("正在計算..."):
        st.session_state.out_df = run_selection()
        st.rerun()

# 顯示區塊 (使用 session_state 確保不會發生 NameError)
if not st.session_state.out_df.empty:
    col1, col2 = st.columns([1, 4])
    with col1:
        selected = st.selectbox("選股清單:", st.session_state.out_df['股票'].tolist())
    with col2:
        draw_zigzag_chart(f"{selected}.TW", selected)
else:
    st.info("請點選左側按鈕以開始選股。")
