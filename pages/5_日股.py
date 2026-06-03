import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 系統設定
st.set_page_config(page_title="日股技術分析系統", layout="wide")
st.title("📈 技術分析波段自動標註系統")

# 1. 數據下載函式
@st.cache_data
def load_data(ticker):
    end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    # 嘗試不同的代號後綴
    suffixes = ["", ".T", ".JP", ".TW", ".TWO"]
    for s in suffixes:
        test_ticker = f"{ticker}{s}" if s != "" else ticker
        df = yf.download(test_ticker, start=start_date, end=end_date)
        if not df.empty:
            return df, test_ticker
    return pd.DataFrame(), None

# 2. UI 輸入區
ticker_input = st.text_input("請輸入股票代號 (例如 4099, 6787, 6227):", "4099")

if ticker_input:
    df, actual_ticker = load_data(ticker_input)
    
    if not df.empty:
        # 資料清理
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna().copy()

        # UI 顯示數值
        st.markdown(f"**分析標的:** `{actual_ticker}`")
        now_5, now_10, now_20 = df['5MA'].iloc[-1], df['10MA'].iloc[-1], df['20MA'].iloc[-1]
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-weight: bold;">
            <span style="color: #FF9800;">5MA: {now_5:.2f}</span> | 
            <span style="color: #000000;">10MA: {now_10:.2f}</span> | 
            <span style="color: #9C27B0;">20MA: {now_20:.2f}</span>
        </div>
        """, unsafe_allow_html=True)

        # 3. 波段邏輯 (ZigZag)
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
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=True)
        
        # 繪製均線：將寬度設定為 0.8 (較細)
        ap = [mpf.make_addplot(df['5MA'], color='orange', width=0.8),
              mpf.make_addplot(df['10MA'], color='black', width=0.8),
              mpf.make_addplot(df['20MA'], color='purple', width=0.8)]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(12, 7), volume=True)
        
        main_ax = axlist[0]
        # 繪製 ZigZag 線：顏色藍色，線條較粗 (1.5)
        if len(zigzag_points) > 1:
            x, y = zip(*zigzag_points)
            main_ax.plot(x, y, color='blue', alpha=0.5, linewidth=1.5, zorder=3)
        
        # 標註 H/B 與數值
        for idx, row in df[df['Label'].notnull()].iterrows():
            x_idx = df.index.get_loc(idx)
            is_h = (row['Label'] == "H")
            val = row['High'] if is_h else row['Low']
            
            # 設定緊湊的偏移量
            v_offset = 20 if is_h else -25 
            
            # 標註 H 或 B
            main_ax.annotate(row['Label'], xy=(x_idx, val), xytext=(0, v_offset),
                             textcoords='offset points', ha='center', 
                             color='red' if is_h else 'green', weight='bold', fontsize=10)
            
            # 標註數值
            main_ax.annotate(f"{val:.0f}", xy=(x_idx, val), xytext=(0, v_offset + (12 if is_h else -12)),
                             textcoords='offset points', ha='center', 
                             color='red' if is_h else 'green', fontsize=8)
        
        st.pyplot(fig)
    else:
        st.error("查無資料，請確認代號是否正確。")
