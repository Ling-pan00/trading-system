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
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330):", "3303")
stock_id = f"{stock_code}.TW" if not ("." in stock_code) else stock_code

# 設定查詢時間範圍：半年
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    return df

try:
    with st.spinner('正在分析中...'):
        df = load_data(stock_id, start_date, end_date)
        
    if df.empty:
        st.error("找不到該股票資料。")
    else:
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. 計算均線
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()

        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        
        df = df.dropna(subset=['Close', '5MA', '20MA']).copy()

        # 2. 轉折波段邏輯 (5MA 交叉)
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        zigzag_points = []
        grouped = df.groupby('State_Group')
        group_ids = sorted(df['State_Group'].unique())

        for g_id in group_ids:
            group_data = grouped.get_group(g_id)
            state = group_data['State'].iloc[0]
            if g_id <= 2: continue
            if state == 1: # 高點
                highest_idx = group_data['High'].idxmax()
                zigzag_points.append((df.index.get_loc(highest_idx), df.loc[highest_idx, 'High']))
                df.loc[highest_idx, 'Label'] = "H"
            else: # 低點
                lowest_idx = group_data['Low'].idxmin()
                zigzag_points.append((df.index.get_loc(lowest_idx), df.loc[lowest_idx, 'Low']))
                df.loc[lowest_idx, 'Label'] = "B"

        # 3. 取得均線趨勢與資訊
        def get_trend_info(col_name):
            now = df[col_name].iloc[-1]
            pre = df[col_name].iloc[-2]
            arrow = "▲" if now >= pre else "▼"
            return f"{col_name}: {now:>8.2f} {arrow}"

        ma5_txt = get_trend_info('5MA')
        ma10_txt = get_trend_info('10MA')
        ma20_txt = get_trend_info('20MA')

        # 4. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # 均線顏色設定
        color_5ma = 'orange'
        color_10ma = 'blue'
        color_20ma = 'purple'

        plots = [
            mpf.make_addplot(df['5MA'], color=color_5ma, width=1),
            mpf.make_addplot(df['10MA'], color=color_10ma, width=1),
            mpf.make_addplot(df['20MA'], color=color_20ma, width=1)
        ]

        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=plots, 
            returnfig=True, figsize=(12, 8), volume=True,
            panel_ratios=(4,1)
        )
        
        main_ax = axlist[0]

        # 【核心修改】在圖表右上角繪製多色文字資訊
        # 先畫一個白底的外框
        main_ax.text(0.98, 0.97, " \n \n ", transform=main_ax.transAxes,
                    fontsize=12, verticalalignment='top', horizontalalignment='right', family='monospace',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.85, edgecolor='gray'))
        
        # 依序在框內填入對應顏色的文字 (調整 y 軸間距 y_space)
        y_start = 0.95
        y_space = 0.035
        
        main_ax.text(0.96, y_start, ma5_txt, transform=main_ax.transAxes, color=color_5ma,
                    fontsize=12, weight='bold', verticalalignment='top', horizontalalignment='right', family='monospace')
        
        main_ax.text(0.96, y_start - y_space, ma10_txt, transform=main_ax.transAxes, color=color_10ma,
                    fontsize=12, weight='bold', verticalalignment='top', horizontalalignment='right', family='monospace')
        
        main_ax.text(0.96, y_start - (y_space * 2), ma20_txt, transform=main_ax.transAxes, color=color_20ma,
                    fontsize=12, weight='bold', verticalalignment='top', horizontalalignment='right', family='monospace')

        # 5. 連接轉折線
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

        # 6. 標註 H/B
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            main_ax.text(x, row['High' if is_h else 'Low'], row['Label'],
                        color='red' if is_h else 'green', weight='bold',
                        ha='center', va='bottom' if is_h else 'top',
                        bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))

        st.pyplot(fig)

except Exception as e:
    st.error(f"執行錯誤: {e}")
