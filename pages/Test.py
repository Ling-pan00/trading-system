import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import twstock
import time

st.set_page_config(page_title="W底診斷器", layout="wide")
st.title("🛠️ W 底自動掃描與診斷工具")

industry_map = {
    "電機機械": "電機機械", "電器電纜": "電器電纜", "化學生技醫療": "生技醫療業",
    "化工": "化學工業", "電子": "電子工業", "半導體": "半導體業",
    "電腦及週邊設備": "電腦及週邊設備業", "光電": "光電業", "通信網路": "通信網路業",
    "電子零組件": "電子零組件業", "電子通路": "電子通路業", "資訊服務": "資訊服務業",
    "其他電子": "其他電子業", "綠能環保": "綠能環保", "數位雲端": "數位雲端"
}

def analyze_ticker(ticker_symbol):
    try:
        # 下載資料
        df = yf.download(ticker_symbol, period="150d", progress=False)
        if len(df) < 60: return None, "資料不足"
        
        close_prices = df['Close'].values.flatten()
        # 參數調小一點 (order=5)，更容易抓到波段底部
        min_indices = argrelextrema(close_prices, np.less_equal, order=5)[0]
        
        if len(min_indices) < 2:
            return None, "未找到兩個底部"
            
        idx1, idx2 = min_indices[-2], min_indices[-1]
        l1, l2 = close_prices[idx1], close_prices[idx2]
        diff_pct = abs(l1 - l2) / l1
        
        # 判斷是否符合 W 底 (誤差 15% 寬鬆設定)
        if diff_pct < 0.15 and (idx2 - idx1) > 5:
            return True, f"符合! 誤差: {diff_pct:.2%}"
        else:
            return False, f"誤差: {diff_pct:.2%}"
    except Exception as e:
        return None, str(e)

selected_industry = st.selectbox("選擇產業：", list(industry_map.keys()))

if st.button("開始診斷掃描"):
    all_codes = twstock.codes
    target_list = [f"{code}.TW" for code, info in all_codes.items() if info.group == industry_map[selected_industry]]
    
    results = []
    # 限制掃描前 20 檔進行診斷，避免等待過久
    for ticker in target_list[:20]:
        is_match, status = analyze_ticker(ticker)
        results.append({"代碼": ticker, "狀態": status, "是否符合": is_match})
    
    st.table(pd.DataFrame(results))
    st.write("💡 如果狀態顯示 '誤差: XX%'，代表程式有抓到兩個低點，只是它們的差距大於設定值。")
