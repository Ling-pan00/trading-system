import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf

st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# 1. 您的 530 檔完整清單 (已確認)
def get_industry_stock_pool():
    # ... (這裡放您那 530 檔完整清單) ...
    return ["1503.TW", "1504.TW", "2303.TW", "2330.TW", "2454.TW", "..."] # 請確保填入完整 530 檔

# 2. 掃描邏輯 (改進：使用批次下載並增加容錯)
if st.button("⚡ 啟動完整 530 檔掃描", type="primary"):
    pool = get_industry_stock_pool()
    results = []
    
    with st.spinner(f"正在分析 {len(pool)} 檔股票，請稍候..."):
        # 一次性大量下載，效率最高
        data = yf.download(pool, period="3mo", group_by='ticker', progress=False)
        
        for s_id in pool:
            try:
                # 取得該檔資料
                df = data[s_id] if isinstance(data.columns, pd.MultiIndex) else data
                if df.empty or 'Close' not in df.columns: continue
                
                # 策略判斷：20日新高 + 增量
                high_20 = df['Close'].rolling(20).max()
                vol_avg_20 = df['Volume'].rolling(20).mean()
                
                if df['Close'].iloc[-1] > high_20.iloc[-2] and df['Volume'].iloc[-1] > (vol_avg_20.iloc[-1] * 2):
                    results.append({"代碼": s_id, "收盤價": round(float(df['Close'].iloc[-1]), 2)})
            except:
                continue # 遇到異常直接跳過，不中斷掃描
                
    st.session_state.scan_results = pd.DataFrame(results)
    st.rerun()

# 3. 繪圖邏輯 (改進：強制欄位格式，避免 ValueError)
if 'scan_results' in st.session_state and st.session_state.scan_results is not None:
    st.table(st.session_state.scan_results)
    
    target = st.selectbox("查看轉折圖", st.session_state.scan_results["代碼"].tolist())
    
    # 強制將欄位轉換為正確格式
    df_plot = yf.download(target, period="3mo", progress=False)
    if not df_plot.empty:
        # 確保欄位為 Open, High, Low, Close, Volume
        df_plot.columns = [c.capitalize() for c in df_plot.columns]
        
        # 進行繪圖
        fig, ax = mpf.plot(df_plot, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
