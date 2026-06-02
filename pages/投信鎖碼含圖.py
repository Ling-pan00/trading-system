import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2 (互動實戰版)")

# --- 1. 投信資料邏輯 (原版) ---
def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except: return None

def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty: all_df.append(df)
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 2. 轉折點與趨勢線計算 ---
def calculate_signals(df):
    # 均線
    df['5MA'] = df['Close'].rolling(5).mean()
    df['10MA'] = df['Close'].rolling(10).mean()
    df['20MA'] = df['Close'].rolling(20).mean()
    
    # 偵測轉折點
    df['Signal'] = None
    # H: 跌破 5MA (找前波高)
    # B: 站上 5MA (找前波低)
    for i in range(1, len(df)):
        if df['Close'].iloc[i] < df['5MA'].iloc[i] and df['Close'].iloc[i-1] >= df['5MA'].iloc[i-1]:
            df.at[df.index[i], 'Signal'] = 'H'
        elif df['Close'].iloc[i] > df['5MA'].iloc[i] and df['Close'].iloc[i-1] <= df['5MA'].iloc[i-1]:
            df.at[df.index[i], 'Signal'] = 'B'
    return df

# --- 3. 互動繪圖 ---
def plot_chart(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
    fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], name='5MA', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['10MA'], name='10MA', line=dict(color='blue')))
    
    # 標註 H 與 B
    h_data = df[df['Signal'] == 'H']
    b_data = df[df['Signal'] == 'B']
    
    fig.add_trace(go.Scatter(x=h_data.index, y=h_data['High'], mode='text', text='H', textfont=dict(color='red', size=15), name='Head'))
    fig.add_trace(go.Scatter(x=b_data.index, y=b_data['Low'], mode='text', text='B', textfont=dict(color='green', size=15), name='Bottom'))
    
    fig.update_layout(title=f"{ticker} 趨勢分析", height=500, xaxis_rangeslider_visible=False)
    return fig

# --- 主程式流程 ---
if st.button("開始 V9.2"):
    with st.spinner("計算鎖碼中..."):
        df_raw = load(30)
        # (這裡省略部分變數處理，請參考您原本的鎖碼邏輯)
        # 假設篩選結果存入 st.session_state.out
        result = [{"股票": "1503"}, {"股票": "1504"}, {"股票": "1521"}] # 測試用
        st.session_state.out = pd.DataFrame(result)

if 'out' in st.session_state:
    col1, col2 = st.columns([1, 4])
    with col1:
        selected = st.radio("鎖碼股:", st.session_state.out['股票'].tolist())
    with col2:
        # 下載 Yahoo 資料並繪圖
        raw_data = yf.download(f"{selected}.TW", period="3mo")
        data = calculate_signals(raw_data)
        st.plotly_chart(plot_chart(data, selected), use_container_width=True)
        
        # 趨勢數據顯示
        last = data.iloc[-1]
        c1, c2, c3 = st.columns(3)
        c1.metric("5MA", f"{last['5MA']:.2f}")
        c2.metric("10MA", f"{last['10MA']:.2f}")
        c3.metric("趨勢", "向上" if last['5MA'] > last['10MA'] else "向下")
