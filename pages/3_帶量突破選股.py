import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("⚡ 策略四：強勢帶量突破系統 (分批掃描版)")

@st.cache_data
def get_full_stock_pool():
    # 請在此處放入您完整的 565 檔清單
    return ["2330.TW", "2317.TW", "2454.TW", "3008.TW", "2303.TW", "2308.TW", "2412.TW"] # ... 填入您的 565 檔

# 繪圖函數保持不變
def draw_zigzag_chart(df, ticker):
    df = df.dropna()
    df.columns = [c.lower() for c in df.columns]
    df['5ma'] = df['close'].rolling(5).mean()
    # ... (其餘轉折繪圖邏輯與之前相同)
    fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 6))
    st.pyplot(fig)

if st.button("⚡ 啟動掃描 (分批下載模式)"):
    pool = get_full_stock_pool()
    start_dt = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    
    # 【核心修正】：將 565 檔分成每批 50 檔下載，防止 API 崩潰
    batch_size = 50
    results = []
    progress_bar = st.progress(0)
    
    for i in range(0, len(pool), batch_size):
        batch = pool[i:i + batch_size]
        progress_bar.progress(i / len(pool))
        
        # 分批下載
        df_batch = yf.download(batch, start=start_dt, auto_adjust=True, group_by='ticker', progress=False)
        
        for s_id in batch:
            df = df_batch[s_id] if isinstance(df_batch.columns, pd.MultiIndex) else df_batch
            if len(df) < 22: continue
            
            # 策略：突破 20 日新高 + 成交量 2 倍
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            
            if df['Close'].iloc[-1] > high_20 and df['Volume'].iloc[-1] > (vol_avg_20 * 2):
                results.append(s_id)
    
    progress_bar.progress(100)
    if results:
        st.session_state['res'] = results
        st.success(f"掃描完成！共篩選出 {len(results)} 檔。")
    else:
        st.info("今日無標的符合條件。")

# 結果診斷區與繪圖區 (與之前相同)
if 'res' in st.session_state:
    sel = st.selectbox("查看詳細走勢", st.session_state['res'])
    if st.button("繪製 K 線"):
        df_single = yf.download(sel, period="6mo", auto_adjust=True, progress=False)
        draw_zigzag_chart(df_single, sel)
