import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定網頁標題
st.title("📈 5MA 轉折波段自動標註系統 (半年區間/多均線版)")

# 讓使用者輸入股票代號
stock_code = st.text_input("請輸入台灣股票代號 (例如: 3303):", "3303")

if not stock_code.endswith(".TW") and not stock_code.endswith(".TWO"):
    stock_id = f"{stock_code}.TW"
else:
    stock_id = stock_code

# 【修改】設定查詢時間範圍：自動抓取當前日期往前推半年的時間
end_date = datetime.today().strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

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

        # 1. 計算 5MA, 10MA, 20MA(月線) 並清洗資料
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean() # 月線

        # 轉換數值型態
        df['Close'] = pd.to_numeric(df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'].iloc[:, 0] if isinstance(df['High'], pd.DataFrame) else df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low'], errors='coerce')
        df['5MA'] = pd.to_numeric(df['5MA'], errors='coerce')
        df['10MA'] = pd.to_numeric(df['10MA'], errors='coerce')
        df['20MA'] = pd.to_numeric(df['20MA'], errors='coerce')
        
        # 剔除尚未算完均線的 NaN 欄位
        df = df.dropna(subset=['Close', '5MA', '10MA', '20MA']).copy()

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
                # 【狀況一：站上5MA波段】最高點
                highest_idx = group_data['High'].idxmax()
                x_pos = df.index.get_loc(highest_idx)
                y_pos = df.loc[highest_idx, 'High']
                
                zigzag_points.append((x_pos, y_pos))
                df.loc[highest_idx, 'Label_Text'] = "H"
                df.loc[highest_idx, 'Label_Pos'] = y_pos * 1.015
                
            elif state == -1:
                # 【狀況二：跌破5MA波段】最低點
                lowest_idx = group_data['Low'].idxmin()
                x_pos = df.index.get_loc(lowest_idx)
                y_pos = df.loc[lowest_idx, 'Low']
                
                zigzag_points.append((x_pos, y_pos))
                df.loc[lowest_idx, 'Label_Text'] = "B"
                df.loc[lowest_idx, 'Label_Pos'] = y_pos * 0.985

        # 【新增】計算均線趨勢方向（最新一天 vs 前一天）
        latest_5ma = df['5MA'].iloc[-1]
        prev_5ma = df['5MA'].iloc[-2]
        trend_5ma = "往上" if latest_5ma >= prev_5ma else "往下"
        delta_5ma = latest_5ma - prev_5ma

        latest_10ma = df['10MA'].iloc[-1]
        prev_10ma = df['10MA'].iloc[-2]
        trend_10ma = "往上" if latest_10ma >= prev_10ma else "往下"
        delta_10ma = latest_10ma - prev_10ma

        latest_20ma = df['20MA'].iloc[-1]
        prev_20ma = df['20MA'].iloc[-2]
        trend_20ma = "往上" if latest_20ma >= prev_20ma else "往下"
        delta_20ma = latest_20ma - prev_20ma

        # 在畫面上呈現均線趨勢指標
        st.subheader("🔮 最新均線趨勢方向")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="5日均線 (5MA)", value=f"{latest_5ma:.2f}", delta=f"{delta_5ma:.2f} ({trend_5ma})")
        with col2:
            st.metric(label="10日均線 (10MA)", value=f"{latest_10ma:.2f}", delta=f"{delta_10ma:.2f} ({trend_10ma})")
        with col3:
            st.metric(label="月線 (20MA)", value=f"{latest_20ma:.2f}", delta=f"{delta_20ma:.2f} ({trend_20ma})")

        # 4. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        # 【修改】多加 10MA 與 20MA 的繪圖參數
        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1.2, label='5MA'),
            mpf.make_addplot(df['10MA'], color='blue', width=1.2, label='10MA'),
            mpf.make_addplot(df['20MA'], color='purple', width=1.2, label='20MA')
        ]

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
        main_ax.legend(loc='upper left') # 顯示均線標籤說明

        # 5. 連接高低轉折點
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='#666666', linestyle='-', linewidth=2.5, label='ZigZag Wave', zorder=3)

        # 6. 標註 H 與 B 的黃色圓角標籤
        for idx, row in df[df['Label_Text'] != ""].iterrows():
            x_pos = df.index.get_loc(idx)
            color = 'red' if row['Label_Text'] == "H" else 'green'
            main_ax.text(
                x_pos, row['Label_Pos'], row['Label_Text'], 
                color=color, fontsize=9, weight='bold', ha='center', va='center', zorder=5,
                bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFCC", alpha=0.9, ec=color, lw=1)
            )

        # 網頁呈現
        st.subheader(f" Bars：{start_date} 至 {end_date} 走勢圖")
        st.pyplot(fig)

except Exception as e:
    st.error(f"程式執行過程中發生錯誤: {e}")
    
