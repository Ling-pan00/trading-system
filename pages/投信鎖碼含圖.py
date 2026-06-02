import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")

# =========================
# 輔助函數：計算 H/B 點與繪圖
# =========================
def get_stock_data(ticker_symbol):
    # 下載近 3 個月數據
    df = yf.download(ticker_symbol + ".TW", period="3mo")
    if df.empty: return None
    
    # 計算均線
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['10MA'] = df['Close'].rolling(window=10).mean()
    df['20MA'] = df['Close'].rolling(window=20).mean()
    
    # 簡單的極值邏輯 (H/B 標記)
    # 這裡實作簡單版本：前日收盤價與今日收盤價的關係判定
    df['Signal'] = ''
    df.loc[(df['Close'] < df['5MA']) & (df['Close'].shift(1) >= df['5MA'].shift(1)), 'Signal'] = 'H'
    df.loc[(df['Close'] > df['5MA']) & (df['Close'].shift(1) <= df['5MA'].shift(1)), 'Signal'] = 'B'
    
    return df

def plot_chart(df, ticker):
    fig = go.Figure()
    # K線
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
    # MA線
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], name='5MA', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['10MA'], name='10MA', line=dict(color='blue')))
    
    # 標記 H 與 B
    h_points = df[df['Signal'] == 'H']
    b_points = df[df['Signal'] == 'B']
    fig.add_trace(go.Scatter(x=h_points.index, y=h_points['High'], mode='text', text='H', textposition='top center', name='Head'))
    fig.add_trace(go.Scatter(x=b_points.index, y=b_points['Low'], mode='text', text='B', textposition='bottom center', name='Bottom'))
    
    fig.update_layout(title=f"{ticker} 技術分析", height=600)
    return fig

# =========================
# 主程式
# =========================
st.title("投信鎖碼股 V9.2（互動實戰版）")

# 模擬您的鎖碼選股結果 (實際應用請放您的選股邏輯)
stock_list = ["1503", "1504", "1513", "1521"]

# 佈局：左邊選單，右邊圖表
col_left, col_right = st.columns([1, 4])

with col_left:
    st.subheader("鎖碼股列表")
    selected_stock = st.radio("選擇股票:", stock_list)

with col_right:
    st.subheader(f"目前顯示: {selected_stock}")
    data = get_stock_data(selected_stock)
    
    if data is not None:
        # 顯示 MA 值
        last = data.iloc[-1]
        m1, m2, m3 = st.columns(3)
        m1.metric("5MA", round(last['5MA'], 2))
        m2.metric("10MA", round(last['10MA'], 2))
        m3.metric("20MA", round(last['20MA'], 2))
        
        # 繪圖
        fig = plot_chart(data, selected_stock)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("無法取得該股數據")
