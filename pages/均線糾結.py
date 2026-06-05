import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import io

# 1. 均線糾結判定函數
def check_tangling(df, periods, threshold):
    mas = {f'MA{p}': df['Close'].rolling(window=p).mean() for p in periods}
    ma_df = pd.DataFrame(mas)
    last_ma = ma_df.iloc[-1]
    
    max_ma = last_ma.max()
    min_ma = last_ma.min()
    
    # 判斷糾結
    is_tangling = (max_ma - min_ma) / min_ma < threshold
    return is_tangling, ma_df

# 2. Streamlit 介面設定
st.title("台股均線糾結選股器")

# 使用者參數輸入
tickers = st.sidebar.text_input("輸入股票代碼 (以逗號分隔)", "2330.TW,2317.TW,2454.TW")
ma_type = st.sidebar.radio("選擇模式", ["3線 (5,10,20)", "4線 (5,10,20,60)"])
threshold = st.sidebar.slider("糾結閾值 (%)", 0.5, 5.0, 2.0) / 100

periods = [5, 10, 20] if "3線" in ma_type else [5, 10, 20, 60]

if st.button("開始掃描"):
    ticker_list = [t.strip() for t in tickers.split(",")]
    found_stocks = []
    
    for t in ticker_list:
        df = yf.download(t, period="6mo", progress=False)
        if len(df) < 60: continue
        
        is_tangled, ma_df = check_tangling(df, periods, threshold)
        
        if is_tangled:
            found_stocks.append(t)
            st.success(f"發現糾結標的: {t}")
            
            # 繪製圖表
            fig, ax = mpf.plot(df.iloc[-100:], type='candle', mav=periods, 
                               volume=True, returnfig=True, figsize=(10, 6))
            st.pyplot(fig)

    if not found_stocks:
        st.warning("未找到符合條件的標的，請嘗試調大閾值。")
