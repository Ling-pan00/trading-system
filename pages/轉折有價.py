import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 系統設定
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330, 4768):", "4768")
end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

@st.cache_data
def load_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

if stock_code:
    df = None
    for ticker in [f"{stock_code}.TW", f"{stock_code}.TWO"]:
        temp = load_data(ticker, start_date, end_date)
        if not temp.empty:
            df = temp
            break
    
    if df is not None:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        
        # 1. 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna(subset=['Close', '5MA', '10MA', '20MA']).copy()

        # 2. 顯示均線數值列
        def get_ma_details(col):
            now, pre = df[col].iloc[-1], df[col].iloc[-2]
            return f"{now:.2f} {'▲' if now >= pre else '▼'}"

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-weight: bold; border-left: 5px solid #6c757d;">
                <span style="color: #FF9800;">5MA: {get_ma_details('5MA')}</span> | 
                <span style="color: #2196F3;">10MA: {get_ma_details('10MA')}</span> | 
                <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
            </div>
        """, unsafe_allow_html=True)

        # 3. 波段邏輯
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        change_indices = df.index[df['State'] != df['State'].shift()].tolist()
        if df.index[-1] not in change_indices: change_indices.append(df.index[-1])
        
        df['Label'] = None
        zigzag_points = []
        for i in range(len(change_indices) - 1):
            subset = df.loc[change_indices[i]:change_indices[i+1]]
            if subset['State'].iloc[0] == 1:
                idx = subset['High'].idxmax()
                df.at[idx, 'Label'] = "H"
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
            else:
                idx = subset['Low'].idxmin()
                df.at[idx, 'Label'] = "B"
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

        # 4. 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [mpf.make_addplot(df['5MA'], color='orange'),
              mpf.make_addplot(df['10MA'], color='blue'),
              mpf.make_addplot(df['20MA'], color='purple')]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(12, 7), volume=True, panel_ratios=(3, 1))
        
        main_ax = axlist[0]
        main_ax.yaxis.tick_right()
        main_ax.yaxis.set_label_position("right")
        
        if len(zigzag_points) > 1:
            x, y = zip(*zigzag_points)
            main_ax.plot(x, y, color='black', alpha=0.5, linewidth=1.5, zorder=3)
            
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            val = row['High'] if is_h else row['Low']
            
            # 標註 H 或 B (去除底色框，直接顯示彩色文字)
            main_ax.annotate(row['Label'], xy=(x, val), xytext=(0, 15 if is_h else -25),
                             textcoords='offset points', ha='center', color='red' if is_h else 'green', 
                             weight='bold', fontsize=12)
            
            # 標註數值 (去除底色框)
            main_ax.annotate(f"{val:.2f}", xy=(x, val), xytext=(0, 30 if is_h else -40),
                             textcoords='offset points', ha='center', weight='bold', fontsize=9,
                             color='red' if is_h else 'green')
                             
        st.pyplot(fig)
