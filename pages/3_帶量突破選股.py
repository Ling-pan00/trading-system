import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import time
import io
import matplotlib.pyplot as plt

# --- 頁面設定 ---
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# --- 股票池 (請確保這裡放入您的完整 530 檔清單) ---
def get_industry_stock_pool():
    # 範例清單，實際執行請確保這是完整的 530 檔
    return ["1503.TW", "1504.TW", "2303.TW", "2330.TW", "2454.TW"] 

# --- 掃描與運算 ---
if 'scan_results' not in st.session_state: st.session_state.scan_results = None

if st.button("⚡ 啟動完整掃描 (分段執行)", type="primary"):
    pool = get_industry_stock_pool()
    results = []
    progress_bar = st.progress(0)
    
    with st.spinner("正在執行分段掃描，請稍候..."):
        # 分段下載，防止 Yahoo 連線中斷
        for i in range(0, len(pool), 20):
            subset = pool[i:i+20]
            try:
                data = yf.download(subset, period="3mo", group_by='ticker', progress=False, auto_adjust=True)
                for s_id in subset:
                    df = data[s_id] if isinstance(data.columns, pd.MultiIndex) else data
                    if df is None or df.empty or 'Close' not in df.columns: continue
                    
                    # 策略：收盤 > 20日最高 且 當日量 > 20日均量 2倍
                    if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and \
                       df['Volume'].iloc[-1] > (df['Volume'].rolling(20).mean().iloc[-1] * 2):
                        results.append({"代碼": s_id, "收盤價": round(float(df['Close'].iloc[-1]), 2)})
            except: continue
            
            progress_bar.progress((i + 20) / len(pool))
            time.sleep(0.5)
            
    st.session_state.scan_results = pd.DataFrame(results)
    st.rerun()

# --- 穩定的繪圖邏輯 ---
if st.session_state.scan_results is not None and not st.session_state.scan_results.empty:
    st.table(st.session_state.scan_results)
    target = st.selectbox("查看轉折圖", st.session_state.scan_results["代碼"].tolist())
    
    if target:
        df = yf.download(target, period="3mo", progress=False, auto_adjust=True)
        if not df.empty and 'Close' in df.columns:
            # 強制欄位名稱大寫 (解決 KeyError)
            df.columns = [c.capitalize() for c in df.columns]
            
            # 使用 BytesIO 緩衝區避免 Streamlit 渲染衝突 (解決 APIException)
            buf = io.BytesIO()
            fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
            fig.savefig(buf, format='png')
            st.image(buf)
            plt.close(fig) # 強制釋放記憶體
        else:
            st.error("該股票目前無有效資料。")
