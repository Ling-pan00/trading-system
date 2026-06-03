import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 設定網頁標題
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 使用者輸入股票代號
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330, 4768):", "4768")

# 設定查詢時間範圍：半年
end_date = datetime.today().strftime('%Y-%m-%d')
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

        # 1. 計算均線
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()

        # 確保數值型態
        for col in ['Close', 'High', 'Low']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 2. 轉折波段邏輯
        df_temp = df.fillna(0).copy()
        df['State'] = np.where(df_temp['Close'] > df_temp['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        # 初始化 Label 欄位
        df['Label'] = np.nan
        zigzag_points = []
        grouped = df.groupby('State_Group')

        for g_id, group_data in grouped:
            if g_id <= 2: continue
            state = group_data['State'].iloc[0]
            if state == 1:
                idx = group_data['High'].idxmax()
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
                df.at[idx, 'Label'] = "H"
            else:
                idx = group_data['Low'].idxmin()
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))
                df.at[idx, 'Label'] = "B"

        # 3. 取得均線數據
        def get_ma_details(col_name):
            data = df[col_name].dropna()
            if len(data) < 2: return "N/A"
            now, pre = data.iloc[-1], data.iloc[-2]
            arrow = "▲" if now >= pre else "▼"
            return f"{now:.2f} {arrow}"

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 5px; margin-top: 10px; margin-bottom: 5px; font-family: monospace; font-size: 15px; font-weight: bold; border-left: 5px solid #6c757d;">
                <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
                <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
                <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
            </div>
        """, unsafe_allow_html=True)

        # 4. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1),
            mpf.make_addplot(df['10MA'], color='blue', width=1),
            mpf.make_addplot(df['20MA'], color='purple', width=1)
        ]

        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=plots, 
            returnfig=True, figsize=(12, 7), volume=True, panel_ratios=(4,1)
        )
        
        main_ax = axlist[0]
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5)

        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            main_ax.text(x, row['High' if is_h else 'Low'], row['Label'],
                        color='red' if is_h else 'green', weight='bold',
                        ha='center', va='bottom' if is_h else 'top',
                        bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))

        st.pyplot(fig)
