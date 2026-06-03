import streamlit as st
import twstock
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="W底自動選股器", layout="wide")
st.title("⚡ 台股 W 底極速掃描器 (全產業版)")

# 自動獲取所有可用產業類別
@st.cache_data
def get_all_industries():
    # twstock 並未直接提供產業清單列表，我們從代碼庫中動態統計
    industries = set()
    for code in twstock.codes:
        group = twstock.codes[code].group
        if group and group != '0': # 過濾掉非產業的代碼
            industries.add(group)
    return sorted(list(industries))

# 使用動態載入的產業列表
all_industry_list = get_all_industries()
selected_industry = st.selectbox("請選擇產業：", all_industry_list)

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
    if df is None or len(df) < 20: return None
    
    close = df['close'].values
    volume = df['capacity'].values
    min_price = min(close[-20:])
    
    # 邏輯判斷
    if abs(close[-1] - min_price) / min_price < 0.05 and volume[-1] > (sum(volume[-20:])/20 * 1.2):
        return "✅ 疑似 W 底且量增"
    return None

if st.button("🚀 開始分析全產業"):
    target_list = [code for code, info in twstock.codes.items() if info.group == selected_industry]
    
    with st.spinner('正在分析中...'):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # 這裡移除掉 [:50] 的限制，讓你掃描完整產業
            results = list(executor.map(lambda c: {"代碼": c, "狀態": analyze_w_bottom(c)}, target_list))
    
    # 過濾只顯示有結果的
    df_results = pd.DataFrame([r for r in results if r["狀態"] is not None])
    if not df_results.empty:
        st.table(df_results)
    else:
        st.info("該產業目前沒有符合條件的標的。")
    st.success("掃描完成！")
