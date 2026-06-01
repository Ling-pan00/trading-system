import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf

# 設定頁面配置
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("📊 565 檔強勢帶量突破選股系統")

# --- 股票池函數 ---
@st.cache_data
def get_industry_stock_pool():
    # 這裡放您的 565 檔清單
    return ["1503.TW", "1504.TW", "1513.TW", "1514.TW", "1519.TW", "1521.TW", "1522.TW", "1524.TW", "1525.TW", "1526.TW", "2330.TW", "2454.TW", "3008.TW"] # 請補齊您的完整清單

# --- 繪圖函數 (修正版) ---
def draw_zigzag_chart(df, ticker):
    # 確保資料格式正確
    df.columns = [c.capitalize() for c in df.columns]
    
    # 計算轉折點
    df['5ma'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5ma'], 1, -1)
    df['State_group'] = (df['State'] != df['State'].shift()).cumsum()
    
    h_points, b_points = [], []
    for _, group in df.groupby('State_group'):
        if len(group) < 2: continue
        if group['State'].iloc[0] == 1:
            idx = group['High'].idxmax()
            h_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
        else:
            idx = group['Low'].idxmin()
            b_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))
            
    # 繪圖
    fig, axlist = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 6), title=f"{ticker} 轉折走勢")
    
    # 畫線與標記
    all_pts = sorted(h_points + b_points)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linestyle='-', linewidth=1.5, zorder=2)
    
    for x, y in h_points:
        axlist[0].text(x, y, 'H', color='red', weight='bold', ha='center', va='bottom', bbox=dict(facecolor='yellow', alpha=0.5, boxstyle='circle'))
    for x, y in b_points:
        axlist[0].text(x, y, 'L', color='blue', weight='bold', ha='center', va='top', bbox=dict(facecolor='cyan', alpha=0.5, boxstyle='circle'))
    
    st.pyplot(fig)

# --- 主程式 ---
if st.button("🚀 啟動掃描"):
    pool = get_industry_stock_pool()
    results = []
    bar = st.progress(0)
    for i, s in enumerate(pool):
        df = yf.download(s, period="2mo", progress=False, auto_adjust=True)
        if len(df) > 20:
            if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and df['Volume'].iloc[-1] > (df['Volume'].iloc[-21:-1].mean() * 2):
                results.append(s)
        bar.progress((i+1)/len(pool))
    st.session_state['res'] = results

if 'res' in st.session_state and st.session_state['res']:
    st.success(f"掃描完成！共 {len(st.session_state['res'])} 檔符合條件")
    sel = st.selectbox("請選擇查看標的", st.session_state['res'])
    
    if st.button("檢視轉折圖"):
        with st.spinner("正在下載資料..."):
            df = yf.download(sel, period="6mo", auto_adjust=True, progress=False)
            if not df.empty and len(df) > 10:
                draw_zigzag_chart(df, sel)
            else:
                st.error("無法下載或數據不足，請稍後再試。")
