import streamlit as st
import twstock
import pandas as pd
import time

st.set_page_config(page_title="W底自動選股器", layout="wide")
st.title("📈 台股產業別 W 底選股器")

# 產業分類映射
industry_map = {
    "電機機械": "電機機械",
    "電器電纜": "電器電纜",
    "半導體": "半導體業",
    "電子工業": "電子工業",
    "電腦及週邊": "電腦及週邊設備業"
}

def analyze_w_bottom(code):
    """判斷 W 底邏輯"""
    try:
        stock = twstock.Stock(code)
        # 獲取近 31 天數據
        data = stock.fetch_31()
        if len(data) < 20: return "資料量不足"
        
        df = pd.DataFrame(data)
        close = df['close'].values
        
        # 簡單 W 底邏輯：
        # 1. 找到近期的最低價格
        # 2. 目前價格是否在該低點附近 (誤差 5%)
        # 3. 確保是在底部區間而非高檔
        min_price = min(close[-20:])
        if abs(close[-1] - min_price) / min_price < 0.05:
            return "✅ 疑似 W 底區間"
        return "震盪整理中"
    except:
        return "資料擷取錯誤"

selected_industry = st.selectbox("請選擇欲掃描的產業：", list(industry_map.keys()))

if st.button("🚀 開始掃描分析"):
    all_codes = twstock.codes
    # 篩選該產業代碼
    target_list = [code for code, info in all_codes.items() if info.group == industry_map[selected_industry]]
    
    results = []
    progress_bar = st.progress(0)
    
    # 進行掃描 (先以該產業前 30 檔為例)
    for i, code in enumerate(target_list[:30]):
        status = analyze_w_bottom(code)
        results.append({"代碼": code, "狀態": status})
        progress_bar.progress((i + 1) / 30)
        time.sleep(0.2)
        
    # 將結果顯示出來
    st.table(pd.DataFrame(results))
    st.success("掃描完成！")
