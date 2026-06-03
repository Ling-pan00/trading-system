import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定網頁標題
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 使用者輸入股票代號
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330, 4768):", "4768")

# 1. 修正：將結束日期設為今天 (包含今天數據)
end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    return df

if stock_code:
    possible_ids = [f"{stock_code}.TW", f"{stock_code}.TWO"]
    df = None
    
    with st.spinner('正在分析中...'):
        for ticker in possible_ids:
            temp_df = load_data(ticker, start_date, end_date)
            if not temp_df.empty:
                df = temp_df
                st.success(f"已成功載入: {ticker}")
                break
        
        if df is None:
            st.error("找不到該股票資料，請檢查代號是否正確。")
            st.stop()

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 基礎處理
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()

        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        
        # 移除空值確保繪圖順暢
        df = df.dropna(subset=['Close', '5MA', '20MA']).copy()

        # 轉折波段邏輯
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        zigzag_points = []
        grouped = df.groupby('State_Group')
        group_ids = sorted(df['State_Group'].unique())

        for g_id in group_ids:
            group_data = grouped.get_group(g_id)
            state = group_data['State'].iloc[0]
            if g_id <= 2: continue
            if state == 1:
                highest_idx = group_data['High'].idxmax()
                zigzag_points.append((df.index.get_loc(highest_idx), df.loc[highest_idx, 'High']))
                df.loc[highest_idx, 'Label'] = "H"
            else:
                lowest_idx = group_data['Low'].idxmin()
                zigzag_points.append((df.index.get_loc(lowest_idx), df.loc[lowest_idx, 'Low']))
                df.loc[lowest_idx, 'Label'] = "B"

        # 顯示 MA 數值
        def get_ma_details(col_name):
            now = df[col_name].iloc[-1]
            pre = df[col_name].iloc[-2]
            arrow = "▲" if now >= pre else "▼"
            return f"{now:.2f} {arrow}"

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 5px; margin-bottom: 5px; font-family: monospace; font-size: 15px; font-weight: bold; border-left: 5px solid #6c757d;">
                <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
                <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
                <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
            </div>
        """, unsafe_allow_html=True)

        # 2. 繪圖設定：調整 panel_ratios
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1),
            mpf.make_addplot(df['10MA'], color='blue', width=1),
            mpf.make_addplot(df['20MA'], color='purple', width=1)
        ]

        # panel_ratios=(2, 1) 表示主圖佔 2/3，成交量圖佔 1/3
        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=plots, 
            returnfig=True, figsize=(12, 8), volume=True,
            panel_ratios=(2, 1) 
        )
        
        main_ax = axlist[0]

        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            main_ax.text(x, row['High' if is_h else 'Low'], row['Label'],
                        color='red' if is_h else 'green', weight='bold',
                        ha='center', va='bottom' if is_h else 'top',
                        bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))

        st.pyplot(fig)
