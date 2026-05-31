import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt

# 設定網頁標題
st.title("📈 5MA 轉折波段自動標註系統")

# 讓使用者在網頁上輸入股票代號 (預設為台積電 2330)
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330):", "2330")

# 台灣股票需要加上 .TW 延伸檔名
if not stock_code.endswith(".TW") and not stock_code.endswith(".TWO"):
    stock_id = f"{stock_code}.TW"
else:
    stock_id = stock_code

# 設定查詢時間範圍
start_date = "2025-01-01"
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
        # =========== 【關鍵修正】解決 yfinance 新版本的多重索引問題 ===========
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # ===================================================================

        # 1. 計算 5MA
        df['5MA'] = df['Close'].rolling(window=5).mean()

        # 2. 資料清洗與型態轉換
        df['Close'] = pd.to_numeric(df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'].iloc[:, 0] if isinstance(df['High'], pd.DataFrame) else df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'].iloc[:, 0] if isinstance(df['Low'], pd.DataFrame) else df['Low'], errors='coerce')
        df['5MA'] = pd.to_numeric(df['5MA'], errors='coerce')
        
        # 刪除算不出 5MA 的前幾天資料
        df = df.dropna(subset=['Close', '5MA']).copy()

        # 3. 定義狀態：1 代表在 5MA 之上，-1 代表在 5MA 之下
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)

        # 4. 找出狀態轉折的起點
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        # 建立儲存標註線的欄位
        df['Target_Line'] = np.nan

        # 5. 開始動態回溯計算
        for i in range(len(df)):
            current_state = df['State'].iloc[i]
            current_group = df['State_Group'].iloc[i]
            
            if current_group <= 2:
                continue
                
            if current_state == 1:
                # 【條件 1】目前站上 5MA，尋找「上一個」頭部區間最低價
                target_group_id = current_group - 2
                prev_head_zone = df[df['State_Group'] == target_group_id]
                if not prev_head_zone.empty:
                    df.loc[df.index[i], 'Target_Line'] = prev_head_zone['Low'].min()
                    
            elif current_state == -1:
                # 【條件 2】目前跌破 5MA，尋找「上一個」底部區間最高價
                target_group_id = current_group - 2
                prev_bottom_zone = df[df['State_Group'] == target_group_id]
                if not prev_bottom_zone.empty:
                    df.loc[df.index[i], 'Target_Line'] = prev_bottom_zone['High'].max()

        # 6. 繪製圖表
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1.5, label='5MA'),
            mpf.make_addplot(df['Target_Line'], color='blue', type='scatter', markersize=25, marker='_', label='Target')
        ]

        fig, ax = mpf.plot(
            df, 
            type='candle', 
            style=s, 
            addplot=plots, 
            returnfig=True, 
            figsize=(12, 6),
            volume=True
        )
        
        st.subheader(f"📊 {stock_id} 歷史K線與動態水平線標註")
        st.pyplot(fig)
        
        st.subheader("📋 最新資料數據確認")
        st.dataframe(df[['Close', '5MA', 'State', 'Target_Line']].tail(10))

except Exception as e:
    st.error(f"程式執行過程中發生錯誤: {e}")
