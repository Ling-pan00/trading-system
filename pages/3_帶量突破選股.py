import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta
import pytz

# 設定頁面
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# 1. 股票池定義
@st.cache_data
def get_industry_stock_pool():
    # 這是您那份正確的 530+ 檔清單
    full_pool = ["1503.TW", "1504.TW", "1513.TW", "2330.TW", "2317.TW", "2454.TW", "3008.TW", "2303.TW", "2412.TW", "2308.TW", "6696.TWO", "8454.TW"] # 請填入您的完整名單
    return sorted(list(set(full_pool)))

# 2. 轉折圖繪圖函數 (獨立於掃描邏輯，保證不衝突)
def draw_zigzag_chart(df, ticker):
    df = df.dropna()
    df.columns = [c.lower() for c in df.columns]
    
    # 計算均線與轉折
    df['5ma'] = df['close'].rolling(5).mean()
    df['state'] = np.where(df['close'] > df['5ma'], 1, -1)
    df['state_group'] = (df['state'] != df['state'].shift()).cumsum()
    
    h_pts, b_pts = [], []
    for _, g in df.groupby('state_group'):
        if len(g) < 2: continue
        if g['state'].iloc[0] == 1:
            idx = g['high'].idxmax()
            h_pts.append((df.index.get_loc(idx), g.loc[idx, 'high']))
        else:
            idx = g['low'].idxmin()
            b_pts.append((df.index.get_loc(idx), g.loc[idx, 'low']))
            
    # 繪圖
    fig, axlist = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 6), title=f"{ticker} 轉折走勢")
    
    # 畫線與標記
    all_pts = sorted(h_pts + b_pts)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linewidth=1.5, zorder=2)
    for x, y in h_pts: axlist[0].text(x, y, 'H', color='red', weight='bold', ha='center', bbox=dict(facecolor='yellow', boxstyle='circle'))
    for x, y in b_pts: axlist[0].text(x, y, 'L', color='blue', weight='bold', ha='center', bbox=dict(facecolor='cyan', boxstyle='circle'))
    st.pyplot(fig)

# 3. 掃描核心 (完全使用您驗證過會跑出 58 檔的邏輯)
if st.button("⚡ 啟動掃描", type="primary"):
    total_pool = get_industry_stock_pool()
    start_dt = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    end_dt = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 正在運算量價模型..."):
        df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
        results = []
        
        for s_id in total_pool:
            df = df_raw[s_id] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            if len(df) < 22: continue
            
            # 策略：突破 20 日新高 + 成交量 2 倍
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            if df['Close'].iloc[-1] > high_20 and df['Volume'].iloc[-1] > (vol_avg_20 * 2):
                results.append(s_id)
                
        if results:
            st.session_state['res'] = results
            st.success(f"掃描完成！發現 {len(results)} 檔標的。")
        else:
            st.info("今日無標的符合條件。")

# 4. 結果顯示與繪圖
if 'res' in st.session_state:
    sel = st.selectbox("選擇要查看轉折圖的標的", st.session_state['res'])
    if st.button("繪製該標的轉折圖"):
        df_single = yf.download(sel, period="6mo", auto_adjust=True, progress=False)
        draw_zigzag_chart(df_single, sel)
