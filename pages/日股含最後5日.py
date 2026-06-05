import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

# 系統設定
st.set_page_config(page_title="日股技術分析系統", layout="wide")
st.title("📈 技術分析波段自動標註系統")

# 1. 數據下載函式
@st.cache_data(ttl=3600) # 設定快取時效，確保盤後更新時能重新獲取
def load_data(ticker):
    # 下載近 180 天資料
    end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    suffixes = ["", ".T", ".JP", ".TW", ".TWO"]
    for s in suffixes:
        test_ticker = f"{ticker}{s}" if s != "" else ticker
        df = yf.download(test_ticker, start=start_date, end=end_date)
        if not df.empty:
            return df, test_ticker
    return pd.DataFrame(), None

# 2. UI 輸入區
ticker_input = st.text_input("請輸入股票代號 (例如 4099, 6787, 6227):", "4099")

if ticker_input:
    df, actual_ticker = load_data(ticker_input)
    
    if not df.empty:
        # 資料清理
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna().copy()

        # --- 優化顯示：顯示當日與近 5 日收盤價 ---
        st.subheader("📊 最近 5 個交易日收盤價")
        # 直接抓取最後 5 筆，確保順序從新到舊
        last_5 = df.tail(5).iloc[::-1]
        
        cols = st.columns(5)
        for i, col in enumerate(cols):
            date_str = last_5.index[i].strftime('%m/%d')
            price = last_5.iloc[i]['Close']
            
            # 計算與前一日的漲跌點數
            if i < 4:
                delta = price - last_5.iloc[i+1]['Close']
            else:
                delta = 0
            
            # 使用 metric 顯示，顏色會隨 delta 自動變色
            col.metric(date_str, f"{price:.2f}", f"{delta:.2f}" if i < 4 else None)
        # ---------------------------------------

        # 趨勢與均線顯示
        st.markdown(f"**分析標的:** `{actual_ticker}` (資料更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M')})")
        
        # ... (後續繪圖邏輯保持不變) ...
        # [此處省略與您原程式相同的繪圖與指標邏輯...]
        
        # 為了簡潔顯示，請將您原本的 mpf 繪圖與 ZigZag 邏輯接在此下方
        # ... (ZigZag 與 st.pyplot(fig) 程式碼) ...

    else:
        st.error("查無資料，請確認代號是否正確。")
