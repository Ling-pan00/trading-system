import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="投信鎖碼系統", layout="wide")

# 初始化
if 'sitc_stock_cache' not in st.session_state: st.session_state.sitc_stock_cache = {}
if 'sitc_report_df' not in st.session_state: st.session_state.sitc_report_df = None

# 請確保您的 565 檔清單完整
def get_full_stock_pool():
    # 這裡放您的完整 565 檔
    return ["2330.TW", "2454.TW", "2317.TW", "3008.TW", "2303.TW", "2308.TW"] # 請務必補齊您的 565 檔

st.title("🏛️ 565 檔投信鎖碼系統")

if st.button("🚀 開始掃描 (請確認清單已填寫)"):
    pool = get_full_stock_pool()
    start_dt = (datetime.now() - timedelta(days=150)).strftime("%Y-%m-%d")
    
    # 下載數據
    with st.spinner("正在下載數據..."):
        df_raw = yf.download(pool, start=start_dt, progress=False)
        
    results = []
    # 針對每一檔進行篩選
    for s in pool:
        try:
            # 取得該檔數據
            df = df_raw.xs(s, axis=1, level=1) if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            df = df.dropna()
            if len(df) < 60: continue
            
            # 計算指標
            df['MA5'] = df['Close'].rolling(5).mean()
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA60'] = df['Close'].rolling(60).mean()
            
            # 策略：站穩月季線 (簡單範例)
            last = df.iloc[-1]
            if last['Close'] > last['MA20'] and last['Close'] > last['MA60']:
                st.session_state.sitc_stock_cache[s] = df
                results.append({'股票代碼': s, '收盤': round(last['Close'], 2)})
        except: continue
        
    st.session_state.sitc_report_df = pd.DataFrame(results)
    st.rerun()

# 顯示結果與繪圖
if st.session_state.sitc_report_df is not None and not st.session_state.sitc_report_df.empty:
    st.write(f"共找到 {len(st.session_state.sitc_report_df)} 檔符合條件")
    ticker = st.selectbox("選擇個股：", st.session_state.sitc_report_df['股票代碼'])
    
    df = st.session_state.sitc_stock_cache[ticker].copy()
    
    # 轉折標註邏輯
    df['State'] = np.where(df['Close'] > df['MA5'], 1, -1)
    df['Label'] = np.where(df['State'] != df['State'].shift(), np.where(df['State'] == 1, 'H', 'B'), np.nan)
    
    # 繪圖
    mc = mpf.make_marketcolors(up='red', down='green')
    s = mpf.make_mpf_style(marketcolors=mc)
    addplots = [mpf.make_addplot(df['MA5'], color='orange'), mpf.make_addplot(df['MA20'], color='purple')]
    
    fig, axlist = mpf.plot(df.tail(60), type='candle', style=s, addplot=addplots, returnfig=True)
    st.pyplot(fig)
else:
    st.warning("目前沒有符合條件的股票，請確認掃描是否完成。")
