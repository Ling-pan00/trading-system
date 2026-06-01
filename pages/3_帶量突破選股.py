import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import time
import io
import matplotlib.pyplot as plt

# 頁面配置
st.set_page_config(page_title="強勢帶量突破選股系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# 股票池定義 (請務必在此處填入完整的 530 檔清單)
def get_industry_stock_pool():
    return ["1503.TW", "1504.TW", "2303.TW", "2330.TW", "2454.TW"] 

# 核心掃描邏輯 (分段執行，確保數據完整)
if 'scan_results' not in st.session_state: st.session_state.scan_results = None

if st.button("⚡ 啟動完整 530 檔掃描"):
    pool = get_industry_stock_pool()
    results = []
    progress_bar = st.progress(0)
    
    with st.spinner("正在進行大數據掃描與運算..."):
        # 分段下載：每 20 檔一批，避免 Yahoo 請求超時
        for i in range(0, len(pool), 20):
            subset = pool[i:i+20]
            try:
                data = yf.download(subset, period="3mo", group_by='ticker', progress=False, auto_adjust=True)
                for s_id in subset:
                    df = data[s_id] if isinstance(data.columns, pd.MultiIndex) else data
                    if df is None or df.empty or 'Close' not in df.columns: continue
                    
                    # 選股策略：收盤 > 20日最高 且 當日量 > 20日均量 2倍
                    if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and \
                       df['Volume'].iloc[-1] > (df['Volume'].rolling(20).mean().iloc[-1] * 2):
                        results.append({"代碼": s_id, "收盤價": round(float(df['Close'].iloc[-1]), 2)})
            except: continue
            
            progress_bar.progress(min((i + 20) / len(pool), 1.0))
            time.sleep(0.5)
            
    st.session_state.scan_results = pd.DataFrame(results)
    st.rerun()

# 繪圖區塊 (採用 BytesIO 記憶體緩衝，徹底杜絕 APIException)
if st.session_state.scan_results is not None and not st.session_state.scan_results.empty:
    st.table(st.session_state.scan_results)
    
    target = st.selectbox("選擇代碼查看轉折圖", st.session_state.scan_results["代碼"].tolist())
    
    if target:
        with st.spinner(f"正在繪製 {target} 趨勢圖..."):
            df = yf.download(target, period="3mo", progress=False, auto_adjust=True)
            
            if not df.empty and 'Close' in df.columns:
                # 正規化欄位名稱為大寫，避開 KeyError
                df.columns = [c.capitalize() for c in df.columns]
                
                # 建立圖表並存入 Buffer
                buf = io.BytesIO()
                fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
                fig.savefig(buf, format='png', bbox_inches='tight')
                
                # 顯示圖片並強制釋放記憶體
                st.image(buf)
                plt.close(fig)
                buf.close()
            else:
                st.error("該檔股票資料異常，無法繪圖。")
