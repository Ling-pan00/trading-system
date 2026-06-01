import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("⚡ 策略四：強勢帶量突破選股系統")
st.caption(f"監控時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 策略：20日新高 + 2倍增量 + ATR止損")

# 這裡放入您原本的股票池列表
def get_industry_stock_pool():
    # (此處省略完整列表，實際運行請貼上您的完整清單)
    return ["2330.TW", "2317.TW", "2303.TW", "2454.TW", "1504.TW"]

total_pool = get_industry_stock_pool()
st.write(f"📊 **帶量突破雷達範圍**：共有 {len(total_pool)} 檔核心標的。")

# 使用 session_state 來儲存結果，避免表格消失
if 'final_results' not in st.session_state: st.session_state.final_results = []

if st.button("⚡ 啟動掃描", type="primary"):
    start_dt = (today_tw - timedelta(days=60)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    results = []
    
    with st.spinner("🚀 正在運算量價與風險模型..."):
        df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
        for s_id in total_pool:
            df = df_raw[s_id] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            if len(df) < 22: continue
            
            # --- 您的原始邏輯完全不變 ---
            df['TR'] = abs(df['High'] - df['Low'])
            df['ATR'] = df['TR'].rolling(window=10).mean()
            last_close = df['Close'].iloc[-1]
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            current_vol = df['Volume'].iloc[-1]
            current_atr = df['ATR'].iloc[-1]
            
            if last_close > high_20 and current_vol > (vol_avg_20 * 2):
                results.append({
                    "代碼": s_id, "建議進場價": round(float(last_close), 2),
                    "ATR止損價": round(float(last_close - current_atr * 1.5), 2)
                })
    st.session_state.final_results = results

# 顯示表格並加入「轉折圖」功能
if st.session_state.final_results:
    st.success(f"掃描完成！發現 {len(st.session_state.final_results)} 檔。")
    st.table(pd.DataFrame(st.session_state.final_results))
    
    st.divider()
    st.subheader("📈 個股轉折趨勢圖 (3個月區間)")
    selected_stock = st.selectbox("請選擇要查看轉折圖的代碼", [r['代碼'] for r in st.session_state.final_results])
    
    # 轉折圖繪製區 (獨立區間為 3 個月)
    start_3m = (today_tw - timedelta(days=90)).strftime("%Y-%m-%d")
    df_3m = yf.download(selected_stock, start=start_3m, progress=False)
    
    # 計算轉折 (5MA)
    df_3m['5MA'] = df_3m['Close'].rolling(5).mean()
    mc = mpf.make_marketcolors(up='red', down='green')
    s = mpf.make_mpf_style(marketcolors=mc)
    
    # 繪圖
    fig, ax = mpf.plot(df_3m, type='candle', style=s, addplot=mpf.make_addplot(df_3m['5MA'], color='orange'), returnfig=True)
    st.pyplot(fig)
