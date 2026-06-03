import streamlit as st
import pandas as pd
import twstock
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

# 設定網頁佈局
st.set_page_config(page_title="投信鎖碼 V9.5", layout="wide")
st.title("投信鎖碼 V9.5（最終修正穩定版）")

# --- 1. 初始化 Session ---
if 'final_out' not in st.session_state:
    st.session_state['final_out'] = pd.DataFrame()

# --- 2. 資料載入核心 ---
@st.cache_data(ttl=3600)
def fetch_twse_data(days=20):
    all_df = []
    today = datetime.today()
    for i in range(days):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.1)
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 3. 選股邏輯 ---
if st.button("🚀 開始執行選股"):
    with st.spinner('正在分析數據中...'):
        df = fetch_twse_data()
        if not df.empty:
            # 自動偵測「買賣超」欄位
            cols = [c for c in df.columns if '買賣超' in c]
            if cols:
                buy_col = cols[0]
                df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
                
                # 簡單邏輯：累積買超大於 0
                out = df.groupby('證券代號')[buy_col].sum().reset_index()
                out = out[out[buy_col] > 0]
                out.columns = ['股票', '累計買超']
                
                st.session_state['final_out'] = out
                st.success(f"篩選完畢，共 {len(out)} 檔標的")
                st.dataframe(out)
            else:
                st.error("無法找到買賣超欄位，請檢查資料結構。")
        else:
            st.error("未抓取到任何資料，請稍後再試。")

# --- 4. 轉折監測器 ---
st.write("---")
st.subheader("🎯 轉折監測器")

if not st.session_state['final_out'].empty:
    out = st.session_state['final_out']
    sel = st.selectbox("請選擇個股：", out['股票'].astype(str).tolist())
    
    try:
        # 使用 twstock 抓取歷史資料 (極度穩定)
        stock = twstock.Stock(sel)
        data = stock.fetch_3mo()
        df_k = pd.DataFrame(data).set_index('date')
        
        if not df_k.empty:
            # 修正欄位名稱以符合 mplfinance
            df_k.columns = ['capacity', 'turnover', 'open', 'high', 'low', 'close', 'change', 'transaction']
            for col in ['open', 'high', 'low', 'close']:
                df_k[col] = pd.to_numeric(df_k[col])
            
            # 繪製 K 線圖
            fig, _ = mpf.plot(df_k.iloc[-60:], type='candle', volume=True, returnfig=True, figsize=(10, 6))
            st.pyplot(fig)
        else:
            st.warning("查無該股票歷史價格。")
    except Exception as e:
        st.error(f"數據繪製異常: {e}")
else:
    st.info("請先點擊上方按鈕執行篩選。")
