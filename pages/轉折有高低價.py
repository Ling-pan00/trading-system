import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 設定網頁標題
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330, 4768):", "4768")

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

        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()

        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        
        df = df.dropna(subset=['Close', '5MA', '20MA']).copy()

        # 1. 轉折狀態判定
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        
        # 2. 轉折波段邏輯：含當日
        # 邏輯：當狀態發生切換的「當日」，回頭找出前一個狀態區間（包含該區間所有日子）的極值
        df['Label'] = None
        zigzag_points = []
        
        # 遍歷資料，尋找狀態切換點
        for i in range(1, len(df)):
            # 如果發現當日狀態與前一日不同，代表發生轉折
            if df['State'].iloc[i] != df['State'].iloc[i-1]:
                
                # 取得前一個狀態的所有 index (直到前一天)
                # 使用iloc切片取得發生切換前的所有資料，確保包含該區間內的所有日子
                prev_data = df.iloc[:i]
                last_group_id = prev_data['State'].iloc[-1]
                prev_group = prev_data[prev_data['State'] == last_group_id]
                
                # 若前一個狀態是 1 (高檔區)，則找最高點
                if last_group_id == 1:
                    idx = prev_group['High'].idxmax()
                    df.loc[idx, 'Label'] = "H"
                    # 確保不重複加入同一點
                    if (df.index.get_loc(idx), df.loc[idx, 'High']) not in zigzag_points:
                        zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
                
                # 若前一個狀態是 -1 (低檔區)，則找最低點
                else:
                    idx = prev_group['Low'].idxmin()
                    df.loc[idx, 'Label'] = "B"
                    if (df.index.get_loc(idx), df.loc[idx, 'Low']) not in zigzag_points:
                        zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

        # 3. 繪圖區塊保持不變
        def get_ma_details(col_name):
            now = df[col_name].iloc[-1]
            pre = df[col_name].iloc[-2]
            arrow = "▲" if now >= pre else "▼"
            return f"{now:.2f} {arrow}"

        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 5px; margin-bottom: 10px; font-family: monospace; font-size: 15px; font-weight: bold; border-left: 5px solid #6c757d;">
                <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
                <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
                <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
            </div>
        """, unsafe_allow_html=True)

        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        plots = [mpf.make_addplot(df['5MA'], color='orange', width=1),
                 mpf.make_addplot(df['10MA'], color='blue', width=1),
                 mpf.make_addplot(df['20MA'], color='purple', width=1)]

        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=plots, returnfig=True, figsize=(12, 7), volume=True, panel_ratios=(3, 1))
        
        main_ax = axlist[0]
        main_ax.yaxis.tick_right()
        main_ax.yaxis.set_label_position("right")
        
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            val = row['High'] if is_h else row['Low']
            color = "red" if is_h else "green"
            main_ax.annotate(row['Label'], xy=(x, val), xytext=(0, 20 if is_h else -20),
                            textcoords='offset points', ha='center', color='white', weight='bold',
                            bbox=dict(boxstyle="circle", fc=color, ec="none"))
            main_ax.annotate(f"{val:.2f}", xy=(x, val), xytext=(0, 45 if is_h else -45),
                            textcoords='offset points', ha='center', color='white', weight='bold', fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none"))

        st.pyplot(fig)
