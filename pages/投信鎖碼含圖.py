import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide", page_title="投信鎖碼 V9.2 穩定版")
st.title("投信鎖碼 V9.2 (已修復 Value Error)")

# 核心數據載入
def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# 繪圖函數：加入異常捕獲
def plot_stock(ticker):
    ticker_str = str(ticker).strip()
    # 嘗試抓取
    for suffix in ['.TW', '.TWO']:
        df = yf.download(f"{ticker_str}{suffix}", period="3mo", progress=False)
        if not df.empty and len(df) > 10: break
    
    if df.empty:
        st.error(f"無法取得 {ticker} 的股價數據，請檢查代號")
        return

    # 格式修正：確保是數值型態
    df = df.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # 計算 MA
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    
    # 繪圖
    apds = [mpf.make_addplot(df[['MA5', 'MA10', 'MA20']])]
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, 
                       volume=True, returnfig=True, figsize=(10, 5))
    st.pyplot(fig)
    plt.close(fig)

# 主邏輯
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty:
        st.error("資料載入失敗")
    else:
        # 尋找關鍵欄位
        stock_col = [c for c in df.columns if '代號' in c][0]
        buy_col = [c for c in df.columns if '買賣超' in c][0]
        
        # 轉換數值：移除逗號，將非數字轉為 0
        df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        result = []
        for stock, g in df.groupby(stock_col):
            g = g.sort_values("date")
            s = g[buy_col].values
            if len(s) < 10: continue
            
            # 您的原始邏輯
            if (s[-3:] < 0).sum() >= 2 or s[-10:].sum() <= 0 or abs(s[-10:].sum()) < 20: continue
            result.append({"股票": stock, "強度": round(s[-3:].sum() / (abs(s[-10:].sum()) + 1), 4)})
        
        st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
        st.rerun()

# 顯示區
if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    selected = st.selectbox("選擇股票:", st.session_state.final_out["股票"].tolist())
    plot_stock(selected)
    st.dataframe(st.session_state.final_out)
