import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import time

st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# 1. 股票池定義
def get_industry_stock_pool():
    # 請在此處確保貼上您那 530 檔完整的清單
    return ["1503.TW", "1504.TW", "2303.TW", "2330.TW", "2454.TW"] 

# 2. 掃描與運算邏輯
if 'scan_results' not in st.session_state: st.session_state.scan_results = None

if st.button("⚡ 啟動完整 530 檔掃描", type="primary"):
    pool = get_industry_stock_pool()
    results = []
    
    with st.spinner("正在進行大數據運算，請稍候..."):
        # 分段下載，避免過多請求導致的 KeyError
        for i in range(0, len(pool), 50):
            subset = pool[i:i+50]
            # 增加 auto_adjust=True 以確保 OHLC 格式統一
            data = yf.download(subset, period="3mo", group_by='ticker', progress=False, auto_adjust=True)
            
            for s_id in subset:
                try:
                    df = data[s_id] if isinstance(data.columns, pd.MultiIndex) else data
                    if df.empty or 'Close' not in df.columns: continue
                    
                    # 策略：收盤 > 20日最高 且 當日量 > 20日均量 2倍
                    if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and \
                       df['Volume'].iloc[-1] > (df['Volume'].rolling(20).mean().iloc[-1] * 2):
                        results.append({"代碼": s_id, "收盤價": round(float(df['Close'].iloc[-1]), 2)})
                except: continue
            time.sleep(0.5)

    st.session_state.scan_results = pd.DataFrame(results)
    st.rerun()

# 3. 繪圖邏輯 (針對 KeyError/ValueError 的強化保護)
if st.session_state.scan_results is not None and not st.session_state.scan_results.empty:
    st.table(st.session_state.scan_results)
    target = st.selectbox("查看轉折圖", st.session_state.scan_results["代碼"].tolist())
    
    # 強制重組資料，排除 Yahoo 回傳資料的各種異構問題
    df_plot = yf.download(target, period="3mo", progress=False, auto_adjust=True)
    
    if not df_plot.empty:
        # 強制將所有欄位名稱大寫，解決 KeyError
        df_plot.columns = [c.capitalize() for c in df_plot.columns]
        
        if 'Close' in df_plot.columns:
            fig, ax = mpf.plot(df_plot, type='candle', style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
        else:
            st.error("目前該檔股票資料無法識別，請稍後再試。")
