import streamlit as st
import twstock
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="W底自動選股器", layout="wide")
st.title("⚡ 台股 W 底極速掃描器")

# 產業分類映射
industry_map = {
    "電機機械": "電機機械",
    "電器電纜": "電器電纜",
    "半導體": "半導體業",
    "電子工業": "電子工業",
    "電腦及週邊": "電腦及週邊設備業"
}

# 關鍵修正：只快取單純的 DataFrame，避開無法序列化的 Stock 物件
@st.cache_data(ttl=3600)
def get_stock_df(code):
    try:
        stock = twstock.Stock(code)
        data = stock.fetch_31()
        if not data: return None
        return pd.DataFrame(data) 
    except:
        return None

def analyze_w_bottom(code):
    df = get_stock_df(code)
    if df is None or len(df) < 20: return "資料量不足"
    
    # 邏輯：檢查最近價格是否在近 20 天最低點的 5% 誤差內
    close = df['close'].values
    min_price = min(close[-20:])
    
    if abs(close[-1] - min_price) / min_price < 0.05:
        return "✅ 疑似 W 底區間"
    return "震盪整理中"

# 介面設定
selected_industry = st.selectbox("請選擇欲掃描的產業：", list(industry_map.keys()))

if st.button("🚀 開始極速掃描分析"):
    target_list = [code for code, info in twstock.codes.items() if info.group == industry_map[selected_industry]]
    
    # 使用 ThreadPoolExecutor 並行處理，確保速度飛快
    with st.spinner('正在分析中，請稍候...'):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # 限制一次掃描 50 檔，避免過度頻繁請求
            results = list(executor.map(lambda c: {"代碼": c, "狀態": analyze_w_bottom(c)}, target_list[:50]))
    
    st.table(pd.DataFrame(results))
    st.success("掃描完成！")
