import streamlit as st
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt

st.title("格式診斷與繪圖")

# 這裡測試最嚴格的資料格式清理
def debug_chart(ticker):
    # 下載數據
    df = yf.download(ticker, period="1mo", progress=False)
    
    # 【關鍵修復】如果 yfinance 回傳的是 MultiIndex (例如: ['Open', '2330.TW'])
    if isinstance(df.columns, tuple) or isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 確保資料是數值，去除空值
    df = df.apply(pd.to_numeric, errors='coerce').dropna()
    
    # 繪圖
    fig, ax = mpf.plot(df, type='candle', style='yahoo', returnfig=True)
    st.pyplot(fig)
    plt.close(fig)

ticker_input = st.text_input("輸入代號 (例如 2330.TW)", "2330.TW")
if st.button("檢測並繪圖"):
    try:
        debug_chart(ticker_input)
        st.success("繪圖成功！")
    except Exception as e:
        st.error(f"錯誤位置: {e}")
        st.exception(e) # 這會直接把詳細 Traceback 印出來
