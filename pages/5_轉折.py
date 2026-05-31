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

        # 2. 轉折波段邏輯
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

        # 3. 取得均線數據與箭頭
        def get_ma_details(col_name):
            now = df[col_name].iloc[-1]
            pre = df[col_name].iloc[-2]
            arrow = "▲" if now >= pre else "▼"
            return f"{now:.2f} {arrow}"

        ma5_info = get_ma_details('5MA')
        ma10_info = get_ma_details('10MA')
        ma20_info = get_ma_details('20MA')

        # 【核心修改】使用 HTML / CSS 在圖表正上方渲染一整條漂亮的均線數據列
        st.markdown(f"""
            <div style="
                background-color: #f8f9fa; 
                padding: 10px 15px; 
                border-radius: 5px; 
                margin-top: 10px; 
                margin-bottom: 5px; 
                font-family: monospace; 
                font-size: 15px; 
                font-weight: bold;
                border-left: 5px solid #6c757d;
            ">
                <span style="color: #FF9800; margin-right: 20px;">5MA: {ma5_info}</span>
                <span style="color: #2196F3; margin-right: 20px;">10MA: {ma10_info}</span>
                <span style="color: #9C27B0;">20MA: {ma20_info}</span>
            </div>
        """, unsafe_allow_html=True)

        # 4. 繪製圖表 (把文字徹底移出這裡，保持圖表內部乾淨)
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1),
            mpf.make_addplot(df['10MA'], color='blue', width=1),
            mpf.make_addplot(df['20MA'], color='purple', width=1)
        ]

        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=plots, 
            returnfig=True, figsize=(12, 7), volume=True,
            panel_ratios=(4,1)
        )
        
        main_ax = axlist[0]

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

        # 網頁呈現圖表
        st.pyplot(fig)

except Exception as e:
    st.error(f"執行錯誤: {e}")
