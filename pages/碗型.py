import streamlit as st
import twstock
import pandas as pd
import numpy as np
import concurrent.futures

st.set_page_config(page_title="台股底部精準掃描器", layout="wide")
st.title("⚡ 台股型態精準掃描器 (月線強勢版)")

@st.cache_data(ttl=3600)
def get_stock_df(code):
    try:
        stock = twstock.Stock(code)
        data = stock.fetch_31()
        if not data or len(data) < 25: return None
        return pd.DataFrame(data)
    except:
        return None

def analyze_w_bottom(code):
    df = get_stock_df(code)
    if df is None: return None
    close = df['close'].values
    volume = df['capacity'].values
    
    # 條件：站上月線 (MA20)
    ma20 = np.mean(close[-20:])
    if close[-1] < ma20: return None
    
    # 條件：W底 + 量增
    min_price = min(close[-20:])
    avg_volume = np.mean(volume[-20:])
    if abs(close[-1] - min_price) / min_price < 0.05 and volume[-1] > (avg_volume * 1.2):
        return f"✅ W底 (收:{close[-1]:.2f})"
    return None

def analyze_saucer_bottom(code):
    df = get_stock_df(code)
    if df is None: return None
    close = df['close'].values
    volume = df['capacity'].values
    
    # 條件：站上月線 (MA20)
    ma20 = np.mean(close[-20:])
    if close[-1] < ma20: return None
    
    mid = len(close) // 2
    # 碗形條件：價格U型 + 底部縮量
    if close[0] > close[mid] and close[-1] > close[mid]:
        bottom_vol = np.mean(volume[mid-5 : mid+5])
        side_vol = np.mean(np.concatenate([volume[:5], volume[-5:]]))
        if bottom_vol < side_vol * 0.6:
            return f"✅ 碗形底 (收:{close[-1]:.2f})"
    return None

# 介面設定
all_industry = sorted(list(set([twstock.codes[c].group for c in twstock.codes if twstock.codes[c].group != '0'])))
selected_industry = st.selectbox("選擇產業：", all_industry)
mode = st.radio("選擇策略：", ["W 底模式", "碗形底模式"])

if st.button("🚀 開始極速掃描"):
    target_list = [code for code, info in twstock.codes.items() if info.group == selected_industry]
    analyze_func = analyze_w_bottom if mode == "W 底模式" else analyze_saucer_bottom
    
    results = []
    with st.spinner('正在過濾強勢股中...'):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_code = {executor.submit(analyze_func, code): code for code in target_list}
            for future in concurrent.futures.as_completed(future_to_code):
                res = future.result()
                if res:
                    results.append({"代碼": future_to_code[future], "狀態": res})
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.info("該產業目前無符合「站上月線」的強勢底部標的。")
