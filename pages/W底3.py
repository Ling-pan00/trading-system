import streamlit as st
import twstock
import pandas as pd
import time

st.title("📊 台股穩定版 W 底選股器")

# 產業分類
industry_map = {"電機機械": "電機機械", "半導體": "半導體業", "電子": "電子工業"}
selected_industry = st.selectbox("請選擇產業：", list(industry_map.keys()))

def get_data_from_twstock(ticker):
    """直接從證交所獲取資料"""
    try:
        code = ticker.replace('.TW', '')
        stock = twstock.Stock(code)
        # 獲取最近 150 天資料
        data = stock.fetch_31() # twstock 限制 fetch 一次為一個月
        # 簡單組合資料
        df = pd.DataFrame(data)
        return df
    except:
        return None

if st.button("開始穩定掃描"):
    all_codes = twstock.codes
    target_list = [f"{code}.TW" for code, info in all_codes.items() if info.group == industry_map[selected_industry]]
    
    results = []
    progress = st.progress(0)
    
    for i, ticker in enumerate(target_list[:10]):
        df = get_data_from_twstock(ticker)
        if df is not None and not df.empty:
            results.append({"代碼": ticker, "狀態": "成功取得資料"})
        else:
            results.append({"代碼": ticker, "狀態": "無法取得資料"})
        progress.progress((i + 1) / 10)
        time.sleep(0.5)
        
    st.table(pd.DataFrame(results))
