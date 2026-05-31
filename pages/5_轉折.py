import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 設定網頁標題
st.title("📈 5MA 轉折波段自動標註系統")

# 讓使用者輸入股票代號
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2313):", "2313")

if not stock_code.endswith(".TW") and not stock_code.endswith(".TWO"):
    stock_id = f"{stock_code}.TW"
else:
    stock_id = stock_code

# 設定查詢時間範圍 (縮短時間讓K線在大螢幕上更清晰、不擁擠)
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
        # 修正 yfinance 新版本的多重索引問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 1. 計算 5MA 並清洗資料
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['Close'] = pd.to_numeric(df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'].iloc[:, 0] if isinstance(df['High'], pd.DataFrame) else df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low'], errors='coerce')
        df['5MA'] = pd.to_numeric(df['5MA'], errors='coerce')
        df = df.dropna(subset=['Close', '5MA']).copy()

        # 2. 定義狀態與群組 (區間切分)
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        # 3. 初始化要標記「頭」、「底」文字的位置與水平線列表
        df['Label_Text'] = ""
        df['Label_Pos'] = np.nan
        horizontal_lines = [] # 用來存要畫的水平線 (價格, 起始時間, 結束時間)

        # 4. 遍歷所有群組，找出每個波段的最高點(頭)與最低點(底)
        grouped = df.groupby('State_Group')
        group_ids = sorted(df['State_Group'].unique())

        for g_id in group_ids:
            group_data = grouped.get_group(g_id)
            state = group_data['State'].iloc[0]
            
            if state == 1:
                # 這是股價在 5MA 之上的波段 -> 找出最高點作為「頭」
                highest_idx = group_data['High'].idxmax()
                df.loc[highest_idx, 'Label_Text'] = "頭"
                df.loc[highest_idx, 'Label_Pos'] = df.loc[highest_idx, 'High'] * 1.01 # 標在最高點上方 1%
            else:
                # 這是股價在 5MA 內下的波段 -> 找出最低點作為「底」
                lowest_idx = group_data['Low'].idxmin()
                df.loc[lowest_idx, 'Label_Text'] = "底"
                df.loc[lowest_idx, 'Label_Pos'] = df.loc[lowest_idx, 'Low'] * 0.99 # 標在最低點下方 1%

        # 5. 計算條件 1 與條件 2 的轉折水平線 (只在轉折第一天觸發)
        df['Is_Turn'] = df['State_Group'] != df['State_Group'].shift()
        
        for i in range(1, len(df)):
            if df['Is_Turn'].iloc[i]: # 今天是轉折的第一天
                current_state = df['State'].iloc[i]
                current_group = df['State_Group'].iloc[i]
                
                if current_group <= 2:
                    continue
                
                # 【條件 1】第一天站上 5MA -> 往前找上一個頭部區間(group - 2)的最低價
                if current_state == 1:
                    prev_head_zone = df[df['State_Group'] == (current_group - 2)]
                    if not prev_head_zone.empty:
                        target_price = prev_head_zone['Low'].min()
                        # 從今天開始畫線，畫到下一次轉折 (下一個 group 的開端)
                        next_turn_data = df[df['State_Group'] == current_group]
                        horizontal_lines.append((target_price, next_turn_data.index[0], next_turn_data.index[-1]))
                        
                # 【條件 2】第一天跌破 5MA -> 往前找上一個底部區間(group - 2)的最高價
                elif current_state == -1:
                    prev_bottom_zone = df[df['State_Group'] == (current_group - 2)]
                    if not prev_bottom_zone.empty:
                        target_price = prev_bottom_zone['High'].max()
                        next_turn_data = df[df['State_Group'] == current_group]
                        horizontal_lines.append((target_price, next_turn_data.index[0], next_turn_data.index[-1]))

        # 6. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # 基礎加載線：5MA
        plots = [mpf.make_addplot(df['5MA'], color='orange', width=1.5, label='5MA')]

        # 使用 returnfig=True 取得 matplotlib 物件進行進階的中文化與畫線處理
        fig, axlist = mpf.plot(
            df, 
            type='candle', 
            style=s, 
            addplot=plots, 
            returnfig=True, 
            figsize=(12, 7),
            volume=True
        )
        
        main_ax = axlist[0] # 主 K 線圖的畫布

        # 解決 Streamlit Cloud 上的中文字型顯示問題 (使用內建系統通用字型)
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Black', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

        # 在圖上動態標註「頭」與「底」的文字
        for idx, row in df[df['Label_Text'] != ""].iterrows():
            # 轉換索引為 mplfinance 內部使用的橫座標數字
            x_pos = df.index.get_loc(idx)
            color = 'red' if row['Label_Text'] == "頭" else 'green'
            main_ax.text(
                x_pos, row['Label_Pos'], row['Label_Text'], 
                color=color, fontsize=12, weight='bold', ha='center',
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=0.6, ec=color)
            )

        # 畫出條件 1 與條件 2 的轉折水平線
        for price, start_date, end_date in horizontal_lines:
            x_start = df.index.get_loc(start_date)
            x_end = df.index.get_loc(end_date)
            main_ax.hlines(y=price, xmin=x_start, xmax=x_end, colors='blue', linestyles='-', linewidth=2)

        # 在網頁上渲染
        st.subheader(f"📊 {stock_id} 轉折波段與頭底標註圖表")
        st.pyplot(fig)

except Exception as e:
    st.error(f"程式執行過程中發生錯誤: {e}")
