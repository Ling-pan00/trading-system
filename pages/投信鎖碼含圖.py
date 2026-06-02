import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（穩定整合版）")

# --- 1. 資料抓取邏輯 (原版) ---
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
        time.sleep(0.05) # 增加延遲避免被證交所封鎖
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 2. 核心繪圖與計算 ---
def get_chart_data(ticker):
    # 確保代號處理正確
    ticker_tw = f"{ticker}.TW"
    df = yf.download(ticker_tw, period="3mo")
    
    # yfinance 新版本回傳可能是 MultiIndex，需修正為單層
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    if df.empty: return None
    
    # 計算 MA
    df['5MA'] = df['Close'].rolling(window=5).mean()
    df['10MA'] = df['Close'].rolling(window=10).mean()
    
    # 轉折標記判定 (增加空值過濾)
    df['Signal'] = None
    for i in range(1, len(df)):
        # 站上 (B)
        if df['Close'].iloc[i] > df['5MA'].iloc[i] and df['Close'].iloc[i-1] <= df['5MA'].iloc[i-1]:
            df.at[df.index[i], 'Signal'] = 'B'
        # 跌破 (H)
        elif df['Close'].iloc[i] < df['5MA'].iloc[i] and df['Close'].iloc[i-1] >= df['5MA'].iloc[i-1]:
            df.at[df.index[i], 'Signal'] = 'H'
    return df

# --- 3. 介面互動區 ---
if st.button("開始 V9.2"):
    with st.spinner("正在運算策略..."):
        raw_df = load(30)
        # 這裡套用你的策略邏輯篩選出 stock_list
        # 為演示，這裡假設篩選結果如下
        st.session_state.out = pd.DataFrame({"股票": ["1503", "1504", "1513", "1521"]})

if 'out' in st.session_state:
    out = st.session_state.out
    col1, col2 = st.columns([1, 4])
    
    with col1:
        selected_stock = st.radio("鎖碼清單:", out['股票'].tolist())
    
    with col2:
        df = get_chart_data(selected_stock)
        if df is not None:
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'))
            fig.add_trace(go.Scatter(x=df.index, y=df['5MA'], name='5MA', line=dict(color='orange', width=2)))
            
            # 畫標記
            h_pts = df[df['Signal'] == 'H']
            b_pts = df[df['Signal'] == 'B']
            fig.add_trace(go.Scatter(x=h_pts.index, y=h_pts['High'], mode='text', text='H', textfont=dict(color='red', size=20)))
            fig.add_trace(go.Scatter(x=b_pts.index, y=b_pts['Low'], mode='text', text='B', textfont=dict(color='green', size=20)))
            
            fig.update_layout(height=500, template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # 趨勢說明
            last = df.iloc[-1]
            st.write(f"當前 5MA: {last['5MA']:.2f} | 10MA: {last['10MA']:.2f}")
        else:
            st.error("查無資料，請確認股票代號。")
