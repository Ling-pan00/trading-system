import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 頁面配置
# ==========================================
st.set_page_config(page_title="投信鎖碼轉折系統", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("📈 投信鎖碼 + 轉折波段分析系統")

if 'sitc_stock_cache' not in st.session_state:
    st.session_state.sitc_stock_cache = {}
if 'sitc_report_df' not in st.session_state:
    st.session_state.sitc_report_df = None

# ==========================================
# 2. 轉折波段計算函式 (核心邏輯)
# ==========================================
def calculate_zigzag(df):
    df = df.copy()
    # 判斷多空狀態
    df['State'] = np.where(df['Close'] > df['MA5'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    df['Label'] = None
    
    # 標記轉折高點(H)與低點(B)
    for g_id in df['State_Group'].unique():
        group_data = df[df['State_Group'] == g_id]
        if len(group_data) < 2: continue
        state = group_data['State'].iloc[0]
        if state == 1: # 多頭波段找高點
            idx = group_data['High'].idxmax()
            df.at[idx, 'Label'] = "H"
        else: # 空頭波段找低點
            idx = group_data['Low'].idxmin()
            df.at[idx, 'Label'] = "B"
    return df

# ==========================================
# 3. 資料處理與掃描 (簡化版池子範例)
# ==========================================
# 請將這裡的 pool 換回你原本完整的 530 檔列表
total_pool = ["2330.TW", "2454.TW", "2317.TW", "2303.TW", "3008.TW"] 

if st.button("🚀 啟動投信掃描", type="primary"):
    start_dt = (today_tw - timedelta(days=180)).strftime("%Y-%m-%d")
    df_raw = yf.download(tickers=total_pool, start=start_dt, group_by='ticker', progress=False)
    
    rows = []
    for s_id in total_pool:
        df = df_raw[s_id].dropna().copy()
        df.columns = [c.title() for c in df.columns]
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        
        # 簡易篩選條件
        if df['Close'].iloc[-1] > df['MA20'].iloc[-1]:
            st.session_state.sitc_stock_cache[s_id] = calculate_zigzag(df)
            rows.append({'股票代碼': s_id, '收盤': round(df['Close'].iloc[-1], 2)})
    
    st.session_state.sitc_report_df = pd.DataFrame(rows)

# ==========================================
# 4. 繪圖區 (mplfinance 專業版)
# ==========================================
if st.session_state.sitc_report_df is not None:
    active_list = list(st.session_state.sitc_stock_cache.keys())
    user_pick = st.selectbox("請選擇個股進行分析：", options=active_list)
    
    if user_pick:
        df = st.session_state.sitc_stock_cache[user_pick].tail(60)
        
        # 設定 mplfinance 風格
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        
        # 設定額外繪圖：均線與轉折點
        ap = [
            mpf.make_addplot(df['MA5'], color='orange', width=1),
            mpf.make_addplot(df['MA20'], color='purple', width=1),
            mpf.make_addplot(df['MA60'], color='blue', width=1)
        ]
        
        # 繪製圖表
        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=ap,
            returnfig=True, figsize=(10, 6), volume=True
        )
        
        # 在主圖標註 H 與 B
        main_ax = axlist[0]
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            main_ax.text(x, row['High'] if is_h else row['Low'], row['Label'],
                         color='white', weight='bold', ha='center',
                         bbox=dict(boxstyle="circle", fc="red" if is_h else "green"))
        
        st.pyplot(fig)
