import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt

# 設定網頁標題
st.title("📈 5MA 轉折波段自動標註系統")

# 讓使用者輸入股票代號
stock_code = st.text_input("請輸入台灣股票代號 (例如: 3303):", "3303")

if not stock_code.endswith(".TW") and not stock_code.endswith(".TWO"):
    stock_id = f"{stock_code}.TW"
else:
    stock_id = stock_code

# 設定查詢時間範圍 (縮短點範圍，畫面呈現會跟手機看盤軟體一樣清晰)
start_date = "2025-11-01"
end_date = "2026-05-30"

@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    return df

try:
    with st.spinner('正在下載股價資料並計算中...'):
        df = load_data(stock_id, start_date, end_date)
        
    if df.empty:
        st.error("找不到該股票資料，請檢查代號是否正確。")
    else:
        # 修正 yfinance 多重索引問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. 計算 5MA 並清洗資料
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['Close'] = pd.to_numeric(df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'].iloc[:, 0] if isinstance(df['High'], pd.DataFrame) else df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low'], errors='coerce')
        df['5MA'] = pd.to_numeric(df['5MA'], errors='coerce')
        df = df.dropna(subset=['Close', '5MA']).copy()

        # 2. 定義狀態與群組 (依據 5MA 交叉動態切分波段)
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        # 3. 找出每個區間的最高點(頭)與最低點(底)，並記錄它們的價格與時間位置
        df['Label_Text'] = ""
        df['Label_Pos'] = np.nan
        
        # 用來存所有轉折點座標的清單，以便後面連線 [(時間索引數字, 價格), ...]
        zigzag_points = []

        grouped = df.groupby('State_Group')
        group_ids = sorted(df['State_Group'].unique())

        for g_id in group_ids:
            group_data = grouped.get_group(g_id)
            state = group_data['State'].iloc[0]
            current_group = g_id
            
            # 跳過最前期的不完整波段，確保有足夠歷史資料回溯
            if current_group <= 2:
                continue
                
            if state == 1:
                # 【條件 1】站上 5MA：往前找上一個頭部區間(current_group - 2)的最低價
                prev_head_zone = df[df['State_Group'] == (current_group - 2)]
                if not prev_head_zone.empty:
                    target_price = prev_head_zone['Low'].min()
                    # 轉折點定在該波段的起點
                    turn_date = group_data.index[0]
                    x_pos = df.index.get_loc(turn_date)
                    zigzag_points.append((x_pos, target_price))
                    
                    # 標記頭部最高點文字 H
                    highest_idx = group_data['High'].idxmax()
                    df.loc[highest_idx, 'Label_Text'] = "H"
                    df.loc[highest_idx, 'Label_Pos'] = df.loc[highest_idx, 'High'] * 1.01
                    
            elif state == -1:
                # 【條件 2】跌破 5MA：往前找上一個底部區間(current_group - 2)的最高價
                prev_bottom_zone = df[df['State_Group'] == (current_group - 2)]
                if not prev_bottom_zone.empty:
                    target_price = prev_bottom_zone['High'].max()
                    # 轉折點定在該波段的起點
                    turn_date = group_data.index[0]
                    x_pos = df.index.get_loc(turn_date)
                    zigzag_points.append((x_pos, target_price))
                    
                    # 標記底部最低點文字 B
                    lowest_idx = group_data['Low'].idxmin()
                    df.loc[lowest_idx, 'Label_Text'] = "B"
                    df.loc[lowest_idx, 'Label_Pos'] = df.loc[lowest_idx, 'Low'] * 0.99

        # 4. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # 先把 5MA 橘線放進基礎圖層
        plots = [mpf.make_addplot(df['5MA'], color='orange', width=1.2, label='5MA')]

        fig, axlist = mpf.plot(
            df, 
            type='candle', 
            style=s, 
            addplot=plots, 
            returnfig=True, 
            figsize=(12, 7),
            volume=True
        )
        
        main_ax = axlist[0] # K線主圖畫布

        # 5. 【關鍵繪圖】將所有轉折點依序連成一條連續不中斷的折線
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            # 畫出深灰色轉折折線 (如同你看盤軟體上的灰色劃線)
            main_ax.plot(x_coords, y_coords, color='#555555', linestyle='-', linewidth=2.5, label='Wave Line', zorder=4)

        # 6. 在 K 線圖上標註 H (頭) 與 B (底) 的黃色圓角標籤
        for idx, row in df[df['Label_Text'] != ""].iterrows():
            x_pos = df.index.get_loc(idx)
            color = 'red' if row['Label_Text'] == "H" else 'green'
            main_ax.text(
                x_pos, row['Label_Pos'], row['Label_Text'], 
                color=color, fontsize=9, weight='bold', ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFCC", alpha=0.9, ec=color, lw=1)
            )

        # 網頁呈現
        st.subheader(f"📊 {stock_id} 轉折波段與頭底連線圖表")
        st.pyplot(fig)

except Exception as e:
    st.error(f"程式執行過程中發生錯誤: {e}")
