import streamlit as st
import pandas as pd
import twstock
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide")
st.title("投信鎖碼 V9.3（核心除錯版）")

# --- 核心：資料載入 ---
def load_data():
    all_df = []
    today = datetime.today()
    for i in range(20):
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
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 按鈕執行區 ---
if st.button("執行篩選"):
    df = load_data()
    # 這裡假設你的核心欄位是這兩個
    stock_col = '證券代號'
    buy_col = '投信買賣超' # 請檢查原始資料欄位名稱是否正確
    
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    # 執行你的鎖碼核心計算
    result = []
    for s, g in df.groupby(stock_col):
        # 簡單篩選邏輯測試
        if g[buy_col].sum() > 50:
            result.append({"股票": s, "買超": g[buy_col].sum()})
            
    out = pd.DataFrame(result)
    st.session_state['final_out'] = out
    st.success(f"篩選到 {len(out)} 檔股票")
    st.dataframe(out)

# --- 轉折監測區 (確保變數存在) ---
if 'final_out' in st.session_state and not st.session_state['final_out'].empty:
    st.subheader("🎯 轉折監測器")
    sel = st.selectbox("選個股：", st.session_state['final_out']["股票"].astype(str).tolist())
    
    # 改用 twstock 抓取
    stock = twstock.Stock(sel)
    data = stock.fetch_3mo()
    df_k = pd.DataFrame(data).set_index('date')
    
    if not df_k.empty:
        # 繪圖
        fig, _ = mpf.plot(df_k.iloc[-60:], type='candle', returnfig=True, volume=True, figsize=(10, 6))
        st.pyplot(fig)
else:
    st.info("尚未篩選出資料，請先執行。")
