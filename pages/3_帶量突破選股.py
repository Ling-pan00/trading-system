import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 頁面配置與股票池 (請確保此處為完整 530 檔)
# ==========================================
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("⚡ 策略四：強勢帶量突破選股系統")
st.caption(f"監控時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 策略：20日新高 + 2倍增量 + ATR止損")

def get_industry_stock_pool():
    # --- 這裡放入您原始的完整 530 檔列表 ---
    return ["1503.TW", "1504.TW", "2330.TW", "2317.TW", "2303.TW", "2454.TW"] 

total_pool = get_industry_stock_pool()
st.write(f"📊 **帶量突破雷達範圍**：共有 {len(total_pool)} 檔核心標的。")

# 使用 Session State 儲存掃描結果，確保表格與選單不會消失
if 'scan_results' not in st.session_state: st.session_state.scan_results = []

# ==========================================
# 2. 掃描核心運算 (原始邏輯不動)
# ==========================================
if st.button("⚡ 啟動掃描", type="primary"):
    start_dt = (today_tw - timedelta(days=60)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    progress_bar = st.progress(0)
    results = []
    
    with st.spinner("🚀 正在運算量價與風險模型..."):
        df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
        
        for idx, s_id in enumerate(total_pool):
            progress_bar.progress((idx + 1) / len(total_pool))
            df = df_raw[s_id] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            if len(df) < 22: continue
            
            # 原始策略指標計算
            df['TR'] = abs(df['High'] - df['Low'])
            df['ATR'] = df['TR'].rolling(window=10).mean()
            last_close = df['Close'].iloc[-1]
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            current_vol = df['Volume'].iloc[-1]
            current_atr = df['ATR'].iloc[-1]
            
            # 原始篩選條件
            if last_close > high_20 and current_vol > (vol_avg_20 * 2):
                results.append({
                    "代碼": s_id, 
                    "建議進場價": round(float(last_close), 2),
                    "ATR止損價": round(float(last_close - current_atr * 1.5), 2),
                    "波動強度": round(current_atr, 2)
                })
    st.session_state.scan_results = results
    st.rerun()

# ==========================================
# 3. 表格顯示與轉折圖 (獨立區間 3 個月)
# ==========================================
if st.session_state.scan_results:
    st.success(f"掃描完成！發現 {len(st.session_state.scan_results)} 檔標的。")
    st.table(pd.DataFrame(st.session_state.scan_results))
    
    st.divider()
    st.subheader("📈 個股轉折趨勢圖 (區間限定：3個月)")
    
    # 下拉選單供使用者選擇
    options = [r['代碼'] for r in st.session_state.scan_results]
    selected_stock = st.selectbox("請選擇代碼以查看轉折趨勢：", options)
    
    # 轉折圖繪製 (限定 3 個月)
    start_3m = (today_tw - timedelta(days=90)).strftime("%Y-%m-%d")
    df_3m = yf.download(selected_stock, start=start_3m, progress=False)
    df_3m['5MA'] = df_3m['Close'].rolling(5).mean()
    
    # 繪圖設定
    mc = mpf.make_marketcolors(up='red', down='green')
    s = mpf.make_mpf_style(marketcolors=mc)
    fig, ax = mpf.plot(df_3m, type='candle', style=s, addplot=mpf.make_addplot(df_3m['5MA'], color='orange'), returnfig=True, figsize=(10, 5))
    
    st.pyplot(fig)
