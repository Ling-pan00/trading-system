import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta
import pytz

# 設定頁面
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")

# 1. 您的完整股票池 (我已將其設為函數，方便維護)
@st.cache_data
def get_full_stock_pool():
    # 這裡放您完整的 565 檔清單
    # ... (請確保這裡放入的是您那份能跑出 58 檔的完整列表)
    return ["1503.TW", "1504.TW", "2330.TW", "2317.TW", "2454.TW", "3008.TW", "2303.TW", "2412.TW", "2308.TW", "6696.TWO", "8454.TW"] 

# 2. 轉折圖繪圖函數 (獨立運作，保證不影響掃描)
def draw_zigzag_chart(df, ticker):
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna()
    
    df['5ma'] = df['close'].rolling(5).mean()
    df['state'] = np.where(df['close'] > df['5ma'], 1, -1)
    df['state_group'] = (df['state'] != df['state'].shift()).cumsum()
    
    h_pts, b_pts = [], []
    for _, g in df.groupby('state_group'):
        if len(g) < 2: continue
        if g['state'].iloc[0] == 1:
            h_pts.append((df.index.get_loc(g['high'].idxmax()), g['high'].max()))
        else:
            b_pts.append((df.index.get_loc(g['low'].idxmin()), g['low'].min()))
            
    fig, axlist = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 6), title=f"{ticker} 轉折走勢")
    
    all_pts = sorted(h_pts + b_pts)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linewidth=1.5, zorder=2)
    for x, y in h_pts: axlist[0].text(x, y, 'H', color='red', weight='bold', ha='center', bbox=dict(facecolor='yellow', boxstyle='circle'))
    for x, y in b_pts: axlist[0].text(x, y, 'L', color='blue', weight='bold', ha='center', bbox=dict(facecolor='cyan', boxstyle='circle'))
    st.pyplot(fig)

# 3. 核心掃描 (使用您驗證過「數量正確」的下載邏輯)
st.title("⚡ 強勢帶量突破選股系統")
if st.button("⚡ 啟動完整掃描"):
    pool = get_full_stock_pool()
    start_dt = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    
    with st.spinner(f"正在掃描 {len(pool)} 檔標的..."):
        # 一次性下載，保證日期對齊 (這是數量正確的關鍵)
        df_raw = yf.download(tickers=pool, start=start_dt, auto_adjust=True, group_by='ticker', progress=False)
        
        results = []
        for s_id in pool:
            df = df_raw[s_id] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            if len(df) < 22: continue
            
            # 使用與您一致的計算邏輯
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            
            if df['Close'].iloc[-1] > high_20 and df['Volume'].iloc[-1] > (vol_avg_20 * 2):
                results.append(s_id)
                
        if results:
            st.session_state['res'] = results
            st.success(f"掃描完成！共發現 {len(results)} 檔。")
        else:
            st.info("無符合條件標的。")

# 4. 結果診斷
if 'res' in st.session_state:
    sel = st.selectbox("選擇要查看轉折圖的標的", st.session_state['res'])
    if st.button("繪製轉折圖"):
        df_single = yf.download(sel, period="6mo", auto_adjust=True, progress=False)
        draw_zigzag_chart(df_single, sel)
