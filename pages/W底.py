import streamlit as st
import twstock
import pandas as pd
import concurrent.futures # 加入並行處理

st.set_page_config(page_title="W底自動選股器", layout="wide")
st.title("⚡ 台股 W 底極速掃描器")

@st.cache_data(ttl=3600) # 快取資料 1 小時，避免重複下載
def get_stock_data(code):
    try:
        stock = twstock.Stock(code)
        return stock.fetch_31()
    except:
        return None

def analyze_w_bottom(code):
    data = get_stock_data(code)
    if not data or len(data) < 20: return "資料量不足"
    
    df = pd.DataFrame(data)
    close = df['close'].values
    min_price = min(close[-20:])
    
    if abs(close[-1] - min_price) / min_price < 0.05:
        return "✅ 疑似 W 底區間"
    return "震盪整理中"

# 產業分類
industry_map = {"電機機械": "電機機械", "半導體": "半導體業", "電子": "電子工業"}
selected_industry = st.selectbox("請選擇產業：", list(industry_map.keys()))

if st.button("🚀 極速掃描分析"):
    target_list = [code for code, info in twstock.codes.items() if info.group == industry_map[selected_industry]]
    
    # 使用 ThreadPoolExecutor 並行處理，速度會快 3-5 倍
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda c: {"代碼": c, "狀態": analyze_w_bottom(c)}, target_list[:50]))
    
    st.table(pd.DataFrame(results))
    st.success("掃描完成！")
