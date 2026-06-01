import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf
import time

# --- 1. 頁面配置 ---
st.set_page_config(page_title="強勢轉折診斷系統", layout="wide")
st.title("📊 565 檔強勢帶量突破選股系統")

# --- 2. 核心函數 ---
@st.cache_data
def get_stock_pool():
    # 這裡填入您完整的 565 檔清單
    return ["2330.TW", "2317.TW", "2454.TW", "3008.TW", "2303.TW", "1503.TW", "2412.TW", "2308.TW"]

def get_clean_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        df['5ma'] = df['close'].rolling(5).mean()
        df['10ma'] = df['close'].rolling(10).mean()
        df['20ma'] = df['close'].rolling(20).mean()
        return df.dropna()
    except: return None

def draw_full_chart(df, ticker):
    # 趨勢資訊
    def get_arrow(col): return "▲" if df[col].iloc[-1] >= df[col].iloc[-2] else "▼"
    st.markdown(f"""
        <div style="background-color: #F0F2F6; padding: 15px; border-radius: 10px; color: black;">
            <div style="display: flex; justify-content: space-around; font-size: 20px; font-weight: bold;">
                <span style="color: #FF8C00;">5MA: {df['5ma'].iloc[-1]:.2f} {get_arrow('5ma')}</span>
                <span style="color: #0000FF;">10MA: {df['10ma'].iloc[-1]:.2f} {get_arrow('10ma')}</span>
                <span style="color: #800080;">20MA: {df['20ma'].iloc[-1]:.2f} {get_arrow('20ma')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Zigzag 計算
    df['state'] = np.where(df['close'] > df['5ma'], 1, -1)
    df['group'] = (df['state'] != df['state'].shift()).cumsum()
    h_pts, b_pts = [], []
    for _, g in df.groupby('group'):
        if len(g) < 2: continue
        if g['state'].iloc[0] == 1:
            idx = g['high'].idxmax()
            h_pts.append((df.index.get_loc(idx), g.loc[idx, 'high']))
        else:
            idx = g['low'].idxmin()
            b_pts.append((df.index.get_loc(idx), g.loc[idx, 'low']))

    # 繪圖
    apds = [mpf.make_addplot(df[['5ma', '10ma', '20ma']]) ]
    fig, axlist = mpf.plot(df, type='candle', style='charles', addplot=apds, returnfig=True, figsize=(10, 6))
    
    # 標記
    all_pts = sorted(h_pts + b_pts)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linewidth=1.5, zorder=2)
    for x, y in h_pts: axlist[0].text(x, y, 'H', color='red', weight='bold', ha='center', bbox=dict(facecolor='yellow', boxstyle='circle', alpha=0.5))
    for x, y in b_pts: axlist[0].text(x, y, 'L', color='blue', weight='bold', ha='center', bbox=dict(facecolor='cyan', boxstyle='circle', alpha=0.5))
    st.pyplot(fig)

# --- 3. 掃描與互動 ---
if st.button("🚀 啟動完整掃描"):
    pool = get_stock_pool()
    results = []
    progress_bar = st.progress(0)
    for i, s in enumerate(pool):
        df = get_clean_data(s)
        if df is not None and len(df) > 20:
            # 放寬後的篩選條件
            if df['close'].iloc[-1] > df['close'].iloc[-21:-1].max():
                results.append(s)
        progress_bar.progress((i+1)/len(pool))
        time.sleep(0.05) # 防封鎖
    st.session_state['res'] = results

if 'res' in st.session_state:
    st.success(f"掃描完成，共 {len(st.session_state['res'])} 檔符合")
    sel = st.selectbox("選擇分析標的", st.session_state['res'])
    if st.button("查看診斷圖"):
        df = get_clean_data(sel)
        draw_full_chart(df, sel)
