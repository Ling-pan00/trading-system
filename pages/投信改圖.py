import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import pytz

# 設定頁面與時區
st.set_page_config(page_title="565檔投信鎖碼系統", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

st.title("🏛️ 策略三：565檔投信鎖碼核心選股系統")

# 初始化 Session State
if 'sitc_stock_cache' not in st.session_state: st.session_state.sitc_stock_cache = {}
if 'sitc_report_df' not in st.session_state: st.session_state.sitc_report_df = None

# ==========================================
# 1. 完整的 565 檔清單函數
# ==========================================
def get_full_stock_pool():
    # 請將您原始的那 565 檔完整的 List 貼在這裡
    # 確保每個元素都是 'XXXX.TW' 或 'XXXX.TWO' 的格式
    return ["2330.TW", "2454.TW", "2317.TW", ...] # (請將您原本的那 565 檔清單貼入此處)

# ==========================================
# 2. 掃描與運算核心
# ==========================================
if st.button("🚀 啟動 565 檔全產業深度掃描", type="primary"):
    pool = get_full_stock_pool()
    progress = st.progress(0)
    
    # 執行與您原始邏輯一致的下載與過濾
    # [此處運行您的篩選條件：投信連買、雙線、週轉率]
    # 將符合條件的 DataFrame 存入 st.session_state.sitc_stock_cache
    st.success("掃描完成")

# ==========================================
# 3. mplfinance 轉折標註 K 線圖
# ==========================================
if st.session_state.sitc_report_df is not None:
    active_stocks = st.session_state.sitc_report_df['股票代碼'].tolist()
    user_pick = st.selectbox("👉 選擇個股進行轉折分析：", options=active_stocks)
    
    if user_pick in st.session_state.sitc_stock_cache:
        df = st.session_state.sitc_stock_cache[user_pick].tail(120).copy()
        
        # --- 轉折邏輯 (ZigZag) ---
        df['State'] = np.where(df['Close'] > df['MA5'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
        
        zigzag_points = []
        for g_id, group in df.groupby('State_Group'):
            if group['State'].iloc[0] == 1:
                idx = group['High'].idxmax()
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
            else:
                idx = group['Low'].idxmin()
                zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

        # --- 繪圖 ---
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc)
        addplots = [
            mpf.make_addplot(df['MA5'], color='orange'),
            mpf.make_addplot(df['MA20'], color='purple'),
            mpf.make_addplot(df['MA60'], color='blue')
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=addplots, returnfig=True, figsize=(10, 6))
        
        # 連接轉折點
        if len(zigzag_points) > 1:
            x, y = zip(*zigzag_points)
            axlist[0].plot(x, y, color='black', alpha=0.5, linewidth=1.5)
            
        st.pyplot(fig)
