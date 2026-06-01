import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import time

# 頁面配置
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# 1. 股票池 (確保此處放的是那 565 檔完整清單)
def get_industry_stock_pool():
    # 請在此處確保放入完整的清單
    return ["1503.TW", "1504.TW", "2303.TW", "2330.TW", "2454.TW"] 

# 2. 核心掃描 (單檔獨立處理，防止資料合併崩潰)
if 'scan_results' not in st.session_state: st.session_state.scan_results = None

if st.button("⚡ 啟動 565 檔防禦性掃描", type="primary"):
    pool = get_industry_stock_pool()
    results = []
    progress_bar = st.progress(0)
    
    with st.spinner("🚀 正在逐檔分析，請稍候..."):
        for i, s_id in enumerate(pool):
            try:
                # 獨立請求，即便該檔數據缺失也不會影響整體迴圈
                df = yf.download(s_id, period="3mo", progress=False, auto_adjust=True)
                
                if df.empty or 'Close' not in df.columns or len(df) < 22:
                    continue
                
                df.columns = [c.capitalize() for c in df.columns]
                
                # 策略計算
                df['Tr'] = abs(df['High'] - df['Low'])
                df['Atr'] = df['Tr'].rolling(window=10).mean()
                
                if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max() and \
                   df['Volume'].iloc[-1] > (df['Volume'].rolling(20).mean().iloc[-1] * 2):
                    results.append({
                        "代碼": s_id, 
                        "進場價": round(float(df['Close'].iloc[-1]), 2),
                        "止損價": round(float(df['Close'].iloc[-1] - df['Atr'].iloc[-1] * 1.5), 2)
                    })
            except:
                continue # 遇到異常直接略過
            
            progress_bar.progress((i + 1) / len(pool))
            # 視需求調整 sleep，若被封鎖則調大一點
            time.sleep(0.1) 
    
    st.session_state.scan_results = pd.DataFrame(results)
    st.rerun()

# 3. 穩定繪圖 (直接繪圖，移除 Buffer 轉換)
if st.session_state.scan_results is not None and not st.session_state.scan_results.empty:
    st.table(st.session_state.scan_results)
    target = st.selectbox("查看轉折圖", st.session_state.scan_results["代碼"].tolist())
    
    if target:
        df = yf.download(target, period="3mo", progress=False, auto_adjust=True)
        if not df.empty and 'Close' in df.columns:
            df.columns = [c.capitalize() for c in df.columns]
            
            # 使用 mplfinance 原生繪圖
            fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
            st.pyplot(fig)
            plt.close(fig) # 確保記憶體釋放
        else:
            st.error("該檔資料異常，無法繪圖。")
