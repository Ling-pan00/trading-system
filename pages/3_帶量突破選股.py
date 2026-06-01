import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="強勢股轉折系統", layout="wide")

# ==========================================
# 1. 股票池與初始化 (Session State)
# ==========================================
if 'results' not in st.session_state: st.session_state.results = []
if 'idx' not in st.session_state: st.session_state.idx = 0

def get_industry_stock_pool():
    # 您的 530 檔清單
    return ["1503.TW", "1504.TW", "1513.TW", "1514.TW", "2330.TW", "2317.TW", "2454.TW", "3008.TW", "4768.TWO"] # ...請填入完整 530 檔

st.title("⚡ 530 檔強勢帶量突破 + 轉折分析系統")

# ==========================================
# 2. 選股掃描邏輯 (3個月區間)
# ==========================================
if st.button("🚀 執行篩選 (3個月區間)", type="primary"):
    total_pool = get_industry_stock_pool()
    start_dt = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    
    scan_temp = []
    with st.spinner("掃描中..."):
        df_raw = yf.download(total_pool, start=start_dt, progress=False)
        for s_id in total_pool:
            df = df_raw[s_id] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            if len(df) < 22: continue
            
            # 策略：突破20日新高 + 2倍均量
            df['ATR'] = (df['High'] - df['Low']).rolling(10).mean()
            vol_avg = df['Volume'].rolling(20).mean()
            if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and df['Volume'].iloc[-1] > (vol_avg.iloc[-1] * 2):
                scan_temp.append({
                    "代碼": s_id,
                    "進場": round(float(df['Close'].iloc[-1]), 2),
                    "止損": round(float(df['Close'].iloc[-1] - df['ATR'].iloc[-1] * 1.5), 2)
                })
    st.session_state.results = scan_temp
    st.session_state.idx = 0
    st.rerun()

# ==========================================
# 3. 逐檔切換看圖
# ==========================================
if st.session_state.results:
    res = st.session_state.results
    idx = st.session_state.idx
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("◀ 上一檔"): st.session_state.idx = max(0, idx - 1); st.rerun()
    with c2:
        st.subheader(f"現正檢視: {res[idx]['代碼']} ({idx+1}/{len(res)})")
    with c3:
        if st.button("下一檔 ▶"): st.session_state.idx = min(len(res)-1, idx + 1); st.rerun()

    # 繪圖
    ticker = res[idx]['代碼']
    df = yf.download(ticker, start=(datetime.now()-timedelta(days=90)).strftime("%Y-%m-%d"), progress=False)
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    
    # 轉折邏輯 (連接點)
    df['Label'] = np.where(df['State'] != df['State'].shift(), np.where(df['State']==1, 'H', 'B'), None)
    
    mc = mpf.make_marketcolors(up='red', down='green')
    s = mpf.make_mpf_style(marketcolors=mc)
    
    # 標記 H/B 點
    apds = [mpf.make_addplot(df['5MA'], color='orange')]
    fig, ax = mpf.plot(df, type='candle', style=s, addplot=apds, returnfig=True)
    
    st.pyplot(fig)
    st.write(f"📊 **建議進場價**: {res[idx]['進場']} | 🛡️ **ATR 止損價**: {res[idx]['止損']}")
