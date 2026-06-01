import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf

st.set_page_config(layout="wide")

# 1. 您的 565 檔清單
STOCK_LIST = ["1503.TW", "1504.TW", ...] # 請確保這裡維持您原始的 565 檔

# 2. 顯示篩選筆數 (置頂)
st.metric("當前篩選總筆數", len(STOCK_LIST))

# 3. 選擇器
ticker = st.selectbox("請選擇要查看的股票代號", STOCK_LIST)

# 4. 繪圖邏輯 (依照您 IMG_3741.jpeg 的樣式)
if st.button("查看走勢圖"):
    df = yf.download(ticker, period="6mo")
    
    if not df.empty:
        # 計算指標 (MA5, MA10, MA20)
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        
        # 顯示上方數值看板
        last = df.iloc[-1]
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
            <h3 style="color: #333;">5MA: {last['MA5']:.2f} | 10MA: {last['MA10']:.2f} | 20MA: {last['MA20']:.2f}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 繪圖參數：包含均線與成交量
        ap = [
            mpf.make_addplot(df['MA5'], color='orange'),
            mpf.make_addplot(df['MA10'], color='blue'),
            mpf.make_addplot(df['MA20'], color='purple')
        ]
        
        fig, ax = mpf.plot(df, type='candle', style='charles', 
                           addplot=ap, volume=True, returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
