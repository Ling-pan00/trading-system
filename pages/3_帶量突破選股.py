import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf

st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("📊 565 檔強勢帶量突破選股系統")

@st.cache_data
def get_industry_stock_pool():
    # 確保您的清單正確
    return ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "3008.TW", "3034.TW", "2308.TW"] # 請填入您的 565 檔完整清單

def draw_zigzag_chart(df, ticker):
    # 【關鍵修正】處理 MultiIndex 與清理欄位
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    df = df.dropna()
    
    # 計算邏輯
    df['5ma'] = df['close'].rolling(5).mean()
    df['state'] = np.where(df['close'] > df['5ma'], 1, -1)
    df['state_group'] = (df['state'] != df['state'].shift()).cumsum()
    
    h_points, b_points = [], []
    for _, group in df.groupby('state_group'):
        if len(group) < 2: continue
        if group['state'].iloc[0] == 1:
            idx = group['high'].idxmax()
            h_points.append((df.index.get_loc(idx), group.loc[idx, 'high']))
        else:
            idx = group['low'].idxmin()
            b_points.append((df.index.get_loc(idx), group.loc[idx, 'low']))
            
    # 【關鍵修正】設定繪圖參數
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', facecolor='white')
    
    fig, axlist = mpf.plot(df, type='candle', style=s, returnfig=True, figsize=(10, 6), title=f"{ticker} 轉折走勢")
    
    all_pts = sorted(h_points + b_points)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linestyle='-', linewidth=1.5, zorder=2)
    
    for x, y in h_points:
        axlist[0].text(x, y, 'H', color='red', fontweight='bold', ha='center', va='bottom', bbox=dict(facecolor='yellow', alpha=0.5, boxstyle='circle'))
    for x, y in b_points:
        axlist[0].text(x, y, 'L', color='blue', fontweight='bold', ha='center', va='top', bbox=dict(facecolor='cyan', alpha=0.5, boxstyle='circle'))
    
    st.pyplot(fig)

# --- 主程式 ---
if st.button("🚀 啟動掃描"):
    pool = get_industry_stock_pool()
    results = []
    bar = st.progress(0)
    for i, s in enumerate(pool):
        try:
            df = yf.download(s, period="2mo", progress=False)
            if len(df) > 20:
                if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and \
                   df['Volume'].iloc[-1] > (df['Volume'].iloc[-21:-1].mean() * 2):
                    results.append(s)
        except: continue
        bar.progress((i+1)/len(pool))
    st.session_state['res'] = results

if 'res' in st.session_state and st.session_state['res']:
    sel = st.selectbox("選擇要查看的標的", st.session_state['res'])
    if st.button("檢視轉折圖"):
        df = yf.download(sel, period="6mo", progress=False)
        if not df.empty:
            draw_zigzag_chart(df, sel)
