import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 強勢突破選股系統 (白底版)")

def get_pool():
    # 這裡放你要的清單
    return ["1503.TW", "1504.TW", "1532.TW"] 

if st.button("🚀 執行篩選"):
    pool = get_pool()
    data = yf.download(pool, period="3mo", group_by='ticker', auto_adjust=True, progress=False)
    
    for t in pool:
        try:
            df = data[t] if len(pool) > 1 else data
            if df.empty: continue
            
            # 設定白底樣式
            mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
            s = mpf.make_mpf_style(marketcolors=mc, facecolor='white', gridstyle='--')
            
            st.subheader(f"✅ {t}")
            fig, ax = mpf.plot(df, type='candle', style=s, volume=True, returnfig=True, figsize=(8, 4))
            st.pyplot(fig)
            plt.close(fig)
        except Exception as e:
            st.error(f"無法繪製 {t}: {e}")
