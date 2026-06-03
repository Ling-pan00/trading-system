import streamlit as st
import twstock
import pandas as pd
import numpy as np
import concurrent.futures

st.set_page_config(page_title="台股底部掃描器", layout="wide")
st.title("⚡ 台股型態極速掃描器")

@st.cache_data(ttl=3600)
def get_stock_df(code):
    try:
        stock = twstock.Stock(code)
        data = stock.fetch_31()
        if not data or len(data) < 30: return None
        return pd.DataFrame(data)
    except:
        return None

def analyze_w_bottom(code):
    df = get_stock_df(code)
    if df is None: return None
    close = df['close'].values
    min_price = min(close[-20:])
    # 簡單 W 底條件：近期低點 + 量增
    if abs(close[-1] - min_price) / min_price < 0.05:
        return "✅ 疑似 W 底"
    return None

def analyze_saucer_bottom(code):
    df = get_stock_df(code)
    if df is None: return None
    close = df['close'].values
    volume = df['capacity'].values
    mid = len(close) // 2
    # 碗形底：U型價格 + 底部縮量
    if close[0] > close[mid] and close[-1] > close[mid]:
        bottom_vol = np.mean(volume[mid-5 : mid+5])
        side_vol = np.mean(np.concatenate([volume[:5], volume[-5:]]))
        if bottom_vol < side_vol * 0.7:
            return "✅ 疑似碗形底"
    return None

# 介面
all_industry = sorted(list(set([twstock.codes[c].group for c in twstock.codes if twstock.codes[c].group != '0'])))
selected_industry = st.selectbox("選擇產業：", all_industry)
mode = st.radio("選擇策略：", ["W 底模式", "碗形底模式"])

if st.button("🚀 開始極速掃描"):
    target_list = [code for code, info in twstock.codes.items() if info.group == selected_industry]
    analyze_func = analyze_w_bottom if mode == "W 底模式" else analyze_saucer_bottom
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(analyze_func, code): code for code in target_list}
        for future in concurrent.futures.as_completed(future_to_code):
            res = future.result()
            if res:
                results.append({"代碼": future_to_code[future], "狀態": res})
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.info("該產業目前無符合條件標的。")
