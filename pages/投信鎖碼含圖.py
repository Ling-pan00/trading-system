import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 設定頁面
st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")

# 1. 狀態初始化 (避免變數消失)
if 'out' not in st.session_state:
    st.session_state.out = pd.DataFrame()

st.title("投信鎖碼股 V9.2")

# 2. 您的核心篩選按鈕 (請將您的 load 和策略放在這裡)
if st.button("開始 V9.2"):
    with st.spinner("正在進行投信策略篩選..."):
        # 這裡放入您原本的 df = load(30) 與策略邏輯
        # 篩選完後，請務必存入 session_state
        # 範例：
        # out = 執行您的篩選邏輯()
        st.session_state.out = out  # <--- 關鍵：存入這裡
        st.rerun()

# 3. 顯示互動介面
if not st.session_state.out.empty:
    out = st.session_state.out
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # 左側清單
        selected_stock = st.radio("選股列表:", out['股票'].tolist())
    
    with col2:
        # 右側繪圖 (依據您選擇的股票)
        st.subheader(f"分析標的: {selected_stock}")
        
        # 這裡放入您的繪圖與技術指標邏輯
        # 使用 yfinance 抓資料，並繪製包含 H, B 標記的圖表
        df = yf.download(f"{selected_stock}.TW", period="3mo")
        
        # ... (這裡放您計算 MA 與找轉折點的邏輯) ...
        
        # 繪圖展示
        fig = go.Figure()
        # ... (將您的圖表加進去) ...
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("請點選左側「開始 V9.2」按鈕以載入篩選結果。")
