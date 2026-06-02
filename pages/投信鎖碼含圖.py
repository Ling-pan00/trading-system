import streamlit as st
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt

st.title("測試繪圖功能")

if st.button("畫一張台積電"):
    with st.spinner("下載中..."):
        # 1. 下載資料
        df = yf.download("2330.TW", period="1mo", progress=False)
        
        # 2. 畫圖 (關鍵：returnfig=True)
        fig, ax = mpf.plot(df, type='candle', style='yahoo', returnfig=True)
        
        # 3. 顯示圖表
        st.pyplot(fig)
        
        # 4. 清理記憶體
        plt.close(fig)
