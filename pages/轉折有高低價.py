import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 設定網頁標題與排版
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330):", "4768")
end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

@st.cache_data
def load_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

if stock_code:
    possible_ids = [f"{stock_code}.TW", f"{stock_code}.TWO"]
    df = None
    for ticker in possible_ids:
        temp_df = load_data(ticker, start_date, end_date)
        if not temp_df.empty:
            df = temp_df
            st.success(f"已成功載入: {ticker}")
            break
    
    if df is not None:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 計算均線
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        
        # 2. 轉折邏輯 (維持先前邏輯)
        df['Cross'] = 0 
        df.loc[(df['Close'] < df['5MA']) & (df['Close'].shift(1) >= df['5MA'].shift(1)), 'Cross'] = -1
        df.loc[(df['Close'] > df['5MA']) & (df['Close'].shift(1) <= df['5MA'].shift(1)), 'Cross'] = 1
        
        labels = {} 
        last_idx = 0
        for idx in df.index[df['Cross'] != 0]:
            segment = df.loc[df.index[last_idx] : idx]
            if df.loc[idx, 'Cross'] == -1:
                peak_idx = segment['High'].idxmax()
                labels[peak_idx] = ('H', df.loc[peak_idx, 'High'])
            else:
                valley_idx = segment['Low'].idxmin()
                labels[valley_idx] = ('B', df.loc[valley_idx, 'Low'])
            last_idx = df.index.get_loc(idx)

        # 3. 均線與趨勢顯示 (補回)
        def get_trend(col): return "▲" if df[col].iloc[-1] >= df[col].iloc[-2] else "▼"
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-weight: bold; border-left: 5px solid #6c757d;">
                5MA: {df['5MA'].iloc[-1]:.2f} {get_trend('5MA')} | 
                10MA: {df['10MA'].iloc[-1]:.2f} {get_trend('10MA')} | 
                月線: {df['20MA'].iloc[-1]:.2f} {get_trend('20MA')}
            </div>
        """, unsafe_allow_html=True)

        # 4. 繪圖 (修復顏色設定與成交量顯示)
        mc = mpf.make_marketcolors(up='red', down='green', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        
        plots = [mpf.make_addplot(df[ma], color=c) for ma, c in zip(['5MA', '10MA', '20MA'], ['orange', 'blue', 'purple'])]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=plots, returnfig=True, figsize=(12, 7), 
                               panel_ratios=(3, 1), volume=True)
        
        # Y軸靠右並修復成交量刻度
        for ax in [axlist[0], axlist[2]]:
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")
        
        # 標註與連線
        points = []
        for idx, (label, val) in labels.items():
            x = df.index.get_loc(idx)
            points.append((x, val))
            color = "red" if label == "H" else "green"
            axlist[0].annotate(label, xy=(x, val), xytext=(0, 20 if label=='H' else -20), 
                             textcoords='offset points', ha='center', color='white', weight='bold',
                             bbox=dict(boxstyle="circle", fc=color, ec="none"))
            axlist[0].annotate(f"{val:.2f}", xy=(x, val), xytext=(0, 45 if label=='H' else -45), 
                             textcoords='offset points', ha='center', color='white', weight='bold', fontsize=9,
                             bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none"))
            
        if len(points) > 1:
            px, py = zip(*points)
            axlist[0].plot(px, py, color='black', alpha=0.5, linewidth=1.5, zorder=3)

        st.pyplot(fig)
