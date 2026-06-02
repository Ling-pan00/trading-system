import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 頁面配置與初始設定
# ==========================================
st.set_page_config(page_title="完整投信鎖碼+轉折分析系統", layout="wide")
st.title("🏛️ 投信鎖碼核心・波段轉折標註系統")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

if 'sitc_stock_cache' not in st.session_state: st.session_state.sitc_stock_cache = {}
if 'sitc_report_df' not in st.session_state: st.session_state.sitc_report_df = None

# 【完整產業清單】
def get_industry_stock_pool():
    # 這裡放您原本的 500+ 檔清單
    return [
        "1503.TW", "1504.TW", "2330.TW", "2454.TW", "3008.TW", "2317.TW", "2303.TW", "2308.TW", 
        "2324.TW", "2357.TW", "2382.TW", "2412.TW", "3045.TW", "3711.TW", "4938.TW", "6669.TW"
        # ... 此處請補上您完整的 500 檔清單 ...
    ]

# ==========================================
# 2. 掃描與運算引擎
# ==========================================
if st.button("🚀 執行全量掃描與波段分析"):
    total_pool = get_industry_stock_pool()
    st.session_state.sitc_stock_cache = {}
    progress_bar = st.progress(0)
    rows = []
    
    with st.spinner("正在進行大量 K 線數據下載與轉折模型演算..."):
        # 批量下載提高效率
        df_raw = yf.download(tickers=total_pool, period="6mo", group_by='ticker', progress=False)
        
        for idx, s_id in enumerate(total_pool):
            progress_bar.progress((idx + 1) / len(total_pool))
            try:
                if s_id not in df_raw.columns.levels[0]: continue
                df = df_raw[s_id].dropna().copy()
                if len(df) < 60: continue
                
                # 指標計算
                df['5MA'] = df['Close'].rolling(5).mean()
                df['20MA'] = df['Close'].rolling(20).mean()
                df['60MA'] = df['Close'].rolling(60).mean()
                
                # 篩選條件：站穩季線與月線
                if df['Close'].iloc[-1] > df['20MA'].iloc[-1] and df['Close'].iloc[-1] > df['60MA'].iloc[-1]:
                    # 轉折標註運算 (ZigZag)
                    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
                    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
                    df['Label'] = None
                    
                    for g_id, group in df.groupby('State_Group'):
                        if g_id <= 2: continue
                        if group['State'].iloc[0] == 1:
                            df.loc[group['High'].idxmax(), 'Label'] = "H"
                        else:
                            df.loc[group['Low'].idxmin(), 'Label'] = "B"
                            
                    st.session_state.sitc_stock_cache[s_id] = df
                    rows.append({'股票代碼': s_id, '最新收盤': round(df['Close'].iloc[-1], 2)})
            except: continue
            
        st.session_state.sitc_report_df = pd.DataFrame(rows)
    progress_bar.empty()

# ==========================================
# 3. 視覺化展示
# ==========================================
if st.session_state.sitc_report_df is not None and not st.session_state.sitc_report_df.empty:
    target = st.selectbox("👉 選擇個股檢視波段轉折", list(st.session_state.sitc_stock_cache.keys()))
    df = st.session_state.sitc_stock_cache[target].tail(100).copy()
    
    # 繪圖參數
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    
    # 準備轉折線數據
    zigzag_points = []
    for idx, row in df.iterrows():
        if row['Label'] in ['H', 'B']:
            zigzag_points.append((df.index.get_loc(idx), row['High'] if row['Label'] == 'H' else row['Low']))
    
    plots = [
        mpf.make_addplot(df['20MA'], color='purple'),
        mpf.make_addplot(df['60MA'], color='blue'),
        mpf.make_addplot(df['5MA'], color='orange', width=0.8)
    ]
    
    fig, axlist = mpf.plot(df, type='candle', style=style, addplot=plots, returnfig=True, figsize=(12, 7), volume=True)
    
    # 繪製轉折連線與標記
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points)
        axlist[0].plot(x, y, color='black', alpha=0.5, linewidth=1.5, zorder=3)
    
    for idx, row in df.iterrows():
        if row['Label'] in ['H', 'B']:
            x = df.index.get_loc(idx)
            axlist[0].text(x, row['High'] if row['Label'] == 'H' else row['Low'], row['Label'], 
                           color='red' if row['Label'] == 'H' else 'green', weight='bold', ha='center',
                           bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))
    
    st.pyplot(fig)
else:
    st.info("請點選上方按鈕開始進行掃描。")
