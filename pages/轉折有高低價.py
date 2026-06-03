import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 設定網頁標題
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 輸入框
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330, 4768):", "4768")

# 日期設定
end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

@st.cache_data
def load_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

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

        # 1. 計算均線
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        df = df.dropna(subset=['Close', '5MA', '20MA']).copy()

        # 2. 轉折波段邏輯
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
        
        zigzag_points = []
        for g_id, group_data in df.groupby('State_Group'):
            if g_id <= 2: continue
            state = group_data['State'].iloc[0]
            if state == 1:
                idx = group_data['High'].idxmax()
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
                df.loc[idx, 'Label'] = "H"
            else:
                idx = group_data['Low'].idxmin()
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))
                df.loc[idx, 'Label'] = "B"

        # 3. 繪圖設定
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=True)

        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1.5),
            mpf.make_addplot(df['10MA'], color='blue', width=1.5),
            mpf.make_addplot(df['20MA'], color='purple', width=1.5)
        ]

        # 繪圖
        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=plots, 
            returnfig=True, figsize=(12, 8), volume=True,
            panel_ratios=(3, 1.2), tight_layout=True
        )
        
        main_ax = axlist[0]
        
        # 繪製轉折線
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='gray', alpha=0.6, linewidth=1.5, zorder=3)

        # 4. 標註 H/B 並顯示價格方框
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            price = row['High'] if is_h else row['Low']
            
            # 圓圈標記
            main_ax.text(x, price, row['Label'], color='white', weight='bold', fontsize=9,
                        ha='center', va='center', zorder=5,
                        bbox=dict(boxstyle="circle,pad=0.2", fc="red" if is_h else "green", ec="none", alpha=0.9))
            
            # 價格方框
            main_ax.annotate(f"{price:.2f}", xy=(x, price),
                            xytext=(0, 25 if is_h else -25), textcoords='offset points',
                            ha='center', va='center', fontsize=8,
                            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                            arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))

        st.pyplot(fig)
