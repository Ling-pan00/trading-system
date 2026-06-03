import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

# 設定頁面資訊
st.set_page_config(page_title="台股產業篩選器", layout="wide")
st.title("📊 台股產業別 W 底選股器")

# 產業分類映射表 (對應 twstock 的分類)
industry_map = {
    "電機機械": "電機機械",
    "電器電纜": "電器電纜",
    "化學生技醫療": "生技醫療業",
    "化工": "化學工業",
    "電子": "電子工業",
    "半導體": "半導體業",
    "電腦及週邊設備": "電腦及週邊設備業",
    "光電": "光電業",
    "通信網路": "通信網路業",
    "電子零組件": "電子零組件業",
    "電子通路": "電子通路業",
    "資訊服務": "資訊服務業",
    "其他電子": "其他電子業",
    "綠能環保": "綠能環保",
    "數位雲端": "數位雲端"
}

def find_w_bottom(ticker_symbol):
    try:
        # 下載 150 天數據
        df = yf.download(ticker_symbol, period="150d", progress=False)
        if len(df) < 60: return False
        
        # 基礎成交量濾網
        if df['Volume'].iloc[-1] < 500: return False
        
        close_prices = df['Close'].values.flatten()
        # 尋找局部極小值
        min_indices = argrelextrema(close_prices, np.less_equal, order=8)[0]
        
        if len(min_indices) >= 2:
            idx1, idx2 = min_indices[-2], min_indices[-1]
            l1, l2 = close_prices[idx1], close_prices[idx2]
            # 寬鬆條件：10% 誤差 + 間隔限制
            if l1 > 0 and abs(l1 - l2) / l1 < 0.10 and (idx2 - idx1) > 5:
                return True
        return False
    except:
        return False

# 介面設定
selected_industry = st.selectbox("請選擇欲掃描的產業類別：", list(industry_map.keys()))

if st.button("🚀 開始掃描該產業"):
    # 獲取 twstock 所有股票資料
    all_codes = twstock.codes
    # 篩選對應產業的股票 (加上 .TW 後綴)
    target_list = [f"{code}.TW" for code, info in all_codes.items() if info.group == industry_map[selected_industry]]
    
    if not target_list:
        st.warning("查無此分類下的股票代碼。")
    else:
        st.write(f"系統正在掃描 {selected_industry}，共 {len(target_list)} 檔...")
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ticker in enumerate(target_list):
            status_text.text(f"分析中: {ticker} ({i+1}/{len(target_list)})")
            
            if find_w_bottom(ticker):
                results.append({"股票代碼": ticker})
            
            progress_bar.progress((i + 1) / len(target_list))
            time.sleep(0.1) # 溫和節奏，避免請求被擋
        
        status_text.text("掃描完成！")
        
        if results:
            st.success(f"發現 {len(results)} 檔標的符合條件：")
            st.table(pd.DataFrame(results))
        else:
            st.info("該產業目前無符合 W 底條件的標的。")

st.sidebar.markdown("### 使用建議")
st.sidebar.write("1. 掃描時請保持網頁開啟。")
st.sidebar.write("2. 若特定產業結果為空，可嘗試切換其他產業。")
