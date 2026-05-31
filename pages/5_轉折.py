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

# 設定查詢時間範圍 (縮短範圍讓K線大小剛好，像手機看盤一樣)
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

        # 2. 定義狀態與群組 (依據 5MA 交叉切分波段)
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        # 3. 初始化標註欄位
        df['Label_Text'] = ""
        df['Label_Pos'] = np.nan
        
        # 用來精確記錄「高低頂點」座標的清單
        zigzag_points = []

        grouped = df.groupby('State_Group')
        group_ids = sorted(df['State_Group'].unique())

        for g_id in group_ids:
            group_data = grouped.get_group(g_id)
            state = group_data['State'].iloc[0]
            
            # 排除前兩組不完整波段
            if g_id <= 2:
                continue
                
            if state == 1:
                # 【狀況一：站上5MA波段】
                # 這個波段的「頭」在當前群組的最高點
                highest_idx = group_data['High'].idxmax()
                x_pos = df.index.get_loc(highest_idx)
                y_pos = df.loc[highest_idx, 'High']
                
                # 記錄轉折點 (連線至此群組最高點)
                zigzag_points.append((x_pos, y_pos))
                
                # 標記 H
                df.loc[highest_idx, 'Label_Text'] = "H"
                df.loc[highest_idx, 'Label_Pos'] = y_pos * 1.015
                
            elif state == -1:
                # 【狀況二：跌破5MA波段】
                # 這個波段的「底」在當前群組的最低點
                lowest_idx = group_data['Low'].idxmin()
                x_pos = df.index.get_loc(lowest_idx)
                y_pos = df.loc[lowest_idx, 'Low']
                
                # 記錄轉折點 (連線至此群組最低點)
                zigzag_points.append((x_pos, y_pos))
                
                # 標記 B
                df.loc[lowest_idx, 'Label_Text'] = "B"
                df.loc[lowest_idx, 'Label_Pos'] = y_pos * 0.985

        # 4. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # 橘色 5MA 線
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

        # 5. 【關鍵修正】把高點 H 與 低點 B 嚴格地高低交叉連起來！
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            # 繪製深灰色鋸齒轉折折線 (zorder=3 確保它穿過 K 線)
            main_ax.plot(x_coords, y_coords, color='#666666', linestyle='-', linewidth=2.5, label='ZigZag Wave', zorder=3)

        # 6. 標註 H 與 B 的黃色圓角標籤 (zorder=5 確保文字在最上層不被線遮擋)
        for idx, row in df[df['Label_Text'] != ""].iterrows():
            x_pos = df.index.get_loc(idx)
            color = 'red' if row['Label_Text'] == "H" else 'green'
            main_ax.text(
                x_pos, row['Label_Pos'], row['Label_Text'], 
                color=color, fontsize=9, weight='bold', ha='center', va='center', zorder=5,
                bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFCC", alpha=0.9, ec=color, lw=1)
            )

        # 網頁呈現
        st.subheader(f"📊 {stock_id} 轉折波段與頭底連線圖表")
        st.pyplot(fig)

except Exception as e:
    st.error(f"程式執行過程中發生錯誤: {e}")
