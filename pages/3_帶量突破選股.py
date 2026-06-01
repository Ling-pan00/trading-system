import streamlit as st
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 強勢突破選股系統 (白底版)")

def get_pool():
    # 請將您的 565 檔清單貼在這裡，格式保持 ['代號', '代號']
    return ["1503.TW", "1504.TW", "1532.TW"] 

if st.button("🚀 開始執行篩選"):
    pool = get_pool()
    # 進行資料下載
    data = yf.download(pool, period="3mo", group_by='ticker', auto_adjust=True, progress=False)
    
    for t in pool:
        try:
            # 確保資料結構正確
            df = data[t] if len(pool) > 1 else data
            if df.empty or len(df) < 20: continue
            
            # 建立圖表物件
            fig, axes = mpf.plot(
                df, type='candle', style='yahoo', 
                volume=True, returnfig=True, 
                figsize=(10, 6), title=t
            )
            
            # 顯示到介面上
            st.subheader(f"✅ 標的：{t}")
            st.pyplot(fig)
            
            # 關鍵：強制清理記憶體，避免下一張圖跑掉
            plt.close('all')
            
        except Exception as e:
            st.write(f"標的 {t} 處理失敗")
            plt.close('all')
