import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. Plotly 轉折繪圖模組 (最穩定的顯示方式) ---
def draw_zigzag_chart(ticker_code, stock_name):
    # 下載數據
    df = yf.download(ticker_code, period="3mo", progress=False)
    if df.empty: return
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 計算 MA
    df['5MA'] = df['Close'].rolling(5).mean()
    df['10MA'] = df['Close'].rolling(10).mean()
    df['20MA'] = df['Close'].rolling(20).mean()
    
    # 轉折點計算
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    
    # 找出 H/B 點
    h_points, b_points = [], []
    for g_id, group in df.groupby('State_Group'):
        if g_id <= 2: continue
        if group['State'].iloc[0] == 1:
            idx = group['High'].idxmax()
            h_points.append({'x': idx, 'y': group.loc[idx, 'High'], 'text': 'H'})
        else:
            idx = group['Low'].idxmin()
            b_points.append({'x': idx, 'y': group.loc[idx, 'Low'], 'text': 'B'})
    
    # 繪圖
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], name='5MA', line=dict(color='orange')))
    
    # 標記 H 與 B
    for p in h_points:
        fig.add_annotation(x=p['x'], y=p['y'], text="H", bgcolor="red", font=dict(color="white"))
    for p in b_points:
        fig.add_annotation(x=p['x'], y=p['y'], text="B", bgcolor="green", font=dict(color="white"))
        
    fig.update_layout(height=500, template="plotly_white", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 2. 主程式與邏輯 ---
st.title("投信鎖碼股 V9.2")
if 'out' not in st.session_state: st.session_state.out = pd.DataFrame()

if st.button("開始 V9.2"):
    # 在這裡放入你的 load(30) 篩選邏輯
    # 假設篩選出：
    st.session_state.out = pd.DataFrame({'股票': ['1503', '1504', '1521']})
    st.rerun()

if not st.session_state.out.empty:
    selected = st.selectbox("選股:", st.session_state.out['股票'].tolist())
    draw_zigzag_chart(f"{selected}.TW", selected)
