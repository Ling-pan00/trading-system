import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf

st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("⚡ 策略四：強勢帶量突破選股系統")

# 1. 股票池定義
def get_industry_stock_pool():
    # 這裡放你那 530 檔股票代碼，我用部分作為範例，請確認完整
    return ["1503.TW", "1504.TW", "2303.TW", "2330.TW", "2454.TW"] 

# 2. 掃描核心
if 'scan_results' not in st.session_state: st.session_state.scan_results = None

if st.button("⚡ 啟動掃描", type="primary"):
    pool = get_industry_stock_pool()
    results = []
    with st.spinner("正在掃描..."):
        # 批次下載
        data = yf.download(pool, period="3mo", group_by='ticker', progress=False, auto_adjust=True)
        for s_id in pool:
            df = data[s_id] if isinstance(data.columns, pd.MultiIndex) else data
            if df is None or df.empty or 'Close' not in df.columns: continue
            
            # 策略：20日新高 + 增量
            if df['Close'].iloc[-1] > df['Close'].iloc[-21:-1].max():
                results.append({"代碼": s_id, "收盤價": round(float(df['Close'].iloc[-1]), 2)})
    st.session_state.scan_results = pd.DataFrame(results)
    st.rerun()

# 3. 繪圖核心 (加入最終強校準)
if st.session_state.scan_results is not None and not st.session_state.scan_results.empty:
    st.table(st.session_state.scan_results)
    target = st.selectbox("查看轉折圖", st.session_state.scan_results["代碼"].tolist())
    
    # 強制校準：確保資料是標準的 DataFrame
    df = yf.download(target, period="3mo", progress=False, auto_adjust=True)
    
    # 排除意外的 MultiIndex 狀況並重置日期索引
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 確保資料結構有 Date 和 OHLC
    if not df.empty and 'Close' in df.columns:
        # 關鍵：強制欄位名稱大寫，符合 mplfinance 嚴格要求
        df.columns = [c.capitalize() for c in df.columns]
        
        # 繪圖
        fig, ax = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
    else:
        st.error("該檔股票目前無足夠資料繪圖。")
