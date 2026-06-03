import streamlit as st
import twstock
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="W底自動選股器", layout="wide")
st.title("⚡ 台股 W 底極速掃描器 (成交量過濾版)")

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
    
    close = df['close'].values
    volume = df['capacity'].values # 獲取成交量
    
    # 1. 基礎 W 底條件：收盤價接近 20 天最低點 (5% 誤差內)
    min_price = min(close[-20:])
    is_bottom = abs(close[-1] - min_price) / min_price < 0.05
    
    # 2.成交量條件：最後一天成交量大於近 20 天平均成交量的 1.2 倍 (代表有量進場)
    avg_volume = sum(volume[-20:]) / 20
    has_volume = volume[-1] > (avg_volume * 1.2)
    
    if is_bottom and has_volume:
        return "✅ 疑似 W 底且量增"
    elif is_bottom:
        return "疑似 W 底 (但量縮)"
    return "震盪整理中"

# 介面與並行處理
industry_map = {"電機機械": "電機機械", "半導體": "半導體業", "電子": "電子工業"}
selected_industry = st.selectbox("請選擇產業：", list(industry_map.keys()))

if st.button("🚀 開始極速分析"):
    target_list = [code for code, info in twstock.codes.items() if info.group == industry_map[selected_industry]]
    
    with st.spinner('正在分析中...'):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor: # 提高 worker 數
            results = list(executor.map(lambda c: {"代碼": c, "狀態": analyze_w_bottom(c)}, target_list[:50]))
    
    # 只顯示疑似 W 底的結果
    df_results = pd.DataFrame(results)
    st.table(df_results[df_results["狀態"].str.contains("✅")])
    st.success("掃描完成！")
