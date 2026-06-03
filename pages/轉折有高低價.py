import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# ==========================================
# 1. 系統設定
# ==========================================
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

# 使用者輸入股票代號
stock_code = st.text_input("請輸入台灣股票代號 (例如: 2330, 4768):", "4768")

# 設定查詢時間範圍：確保包含今日
end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
# 向前抓取 180 天的資料，確保有足夠的時間計算均線與波段
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

# ==========================================
# 2. 資料載入 (快取)
# ==========================================
@st.cache_data
def load_data(ticker, start, end):
    df = yf.download(ticker, start=start, end=end)
    return df

if stock_code:
    # 同時嘗試 .TW (上市) 與 .TWO (上櫃)
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

        # 處理 MultiIndex 欄位 (yfinance 升級後常出現的問題)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 確保資料為數值型態
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')

        # ==========================================
        # 3. 計算均線
        # ==========================================
        df['5MA'] = df['Close'].rolling(window=5).mean()
        df['10MA'] = df['Close'].rolling(window=10).mean()
        df['20MA'] = df['Close'].rolling(window=20).mean()
        
        # 刪除 NaN 值 (剛開始計算 MA 的日子)
        df = df.dropna(subset=['Close', '5MA', '20MA']).copy()

        # ==========================================
        # 4. 轉折波段邏輯 (微調版：含當日)
        # ==========================================
        # 建立狀態欄位：1 為在 5MA 之上，-1 為在 5MA 之下
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        # 建立群組欄位：當狀態切換時，群組編號會增加
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

        zigzag_points = []
        df['Label'] = None
        grouped = df.groupby('State_Group')
        
        # 獲取所有群組編號，並排序
        group_ids = sorted(df['State_Group'].unique())

        for i in range(len(group_ids)):
            g_id = group_ids[i]
            group_data = grouped.get_group(g_id)
            state = group_data['State'].iloc[0]
            
            # 您提到的條件，邏輯上會自動排除第一個群組，
            # 因為第一個群組沒有前一個「底區間」或「頭區間」。
            if g_id <= 2: continue
            
            # 若目前狀態是 1 (高檔區)，表示跌破了前一個區間，
            # 依條件 1：找上一個底區間 (state == -1) 的最高價
            if state == 1:
                # 這裡抓取 *前一個* 群組
                prev_g_id = group_ids[i-1]
                prev_group_data = grouped.get_group(prev_g_id)
                # 確保前一個區間真的是底區間 (-1)
                if prev_group_data['State'].iloc[0] == -1:
                    lowest_idx = prev_group_data['Low'].idxmin()
                    # 依您的描述，這裡應該是標註底 (B)
                    # zigzag_points 記錄轉折點供繪圖
                    zigzag_points.append((df.index.get_loc(lowest_idx), df.loc[lowest_idx, 'Low']))
                    df.loc[lowest_idx, 'Label'] = "B"
            
            # 若目前狀態是 -1 (低檔區)，表示站上了前一個區間，
            # 依條件 2：找上一個頭區間 (state == 1) 的最低價
            else:
                prev_g_id = group_ids[i-1]
                prev_group_data = grouped.get_group(prev_g_id)
                if prev_group_data['State'].iloc[0] == 1:
                    highest_idx = prev_group_data['High'].idxmax()
                    # 依您的描述，這裡應該是標註頭 (H)
                    zigzag_points.append((df.index.get_loc(highest_idx), df.loc[highest_idx, 'High']))
                    df.loc[highest_idx, 'Label'] = "H"

        # **重要優化**：處理最新的波段
        # 如果最後一個群組在 5MA 之上，且沒有產生 'B' 標記，回溯標註
        last_g_id = group_ids[-1]
        last_group_data = df[df['State_Group'] == last_g_id]
        if last_group_data['Label'].isnull().all():
            if last_group_data['State'].iloc[0] == 1:
                idx = last_group_data['High'].idxmax()
                df.loc[idx, 'Label'] = "H"
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
            else:
                idx = last_group_data['Low'].idxmin()
                df.loc[idx, 'Label'] = "B"
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

        # ==========================================
        # 5. 均線數據顯示
        # ==========================================
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

        # ==========================================
        # 6. 繪製圖表
        # ==========================================
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

        plots = [
            mpf.make_addplot(df['5MA'], color='orange', width=1),
            mpf.make_addplot(df['10MA'], color='blue', width=1),
            mpf.make_addplot(df['20MA'], color='purple', width=1)
        ]

        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=plots, 
            returnfig=True, figsize=(12, 7), volume=True,
            panel_ratios=(3, 1) # 設定成交量比例
        )
        
        main_ax = axlist[0]
        volume_ax = axlist[2]

        # 強制 Y 軸數值靠右
        main_ax.yaxis.tick_right()
        main_ax.yaxis.set_label_position("right")
        volume_ax.yaxis.tick_right()
        volume_ax.yaxis.set_label_position("right")

        # 連接轉折線
        if len(zigzag_points) > 1:
            x_coords, y_coords = zip(*zigzag_points)
            main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

        # 標註 H/B 與價格數值
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            # 依您的標註位置微調：H 標高點，B 標低點
            val = row['High'] if is_h else row['Low']
            color = "red" if is_h else "green"
            
            # 圓圈標記
            main_ax.annotate(row['Label'], xy=(x, val), xytext=(0, 20 if is_h else -20),
                            textcoords='offset points', ha='center', va='center',
                            color='white', weight='bold',
                            bbox=dict(boxstyle="circle", fc=color, ec="none", alpha=1))
            
            # 價格數值框
            main_ax.annotate(f"{val:.2f}", xy=(x, val), xytext=(0, 45 if is_h else -45),
                            textcoords='offset points', ha='center', va='center',
                            color='white', weight='bold', fontsize=9,
                            bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none", alpha=1))

        # 顯示圖表
        st.pyplot(fig)
