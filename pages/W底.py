import streamlit as st
import twstock
import pandas as pd
import concurrent.futures

st.set_page_config(page_title="W底極速選股", layout="wide")
st.title("⚡ 閃電版台股 W 底選股器")

@st.cache_data(ttl=3600)
def get_stock_df(code):
    try:
        # 直接使用 fetch_31 抓取資料並轉為精簡的 DataFrame
        stock = twstock.Stock(code)
        data = stock.fetch_31()
        if not data: return None
        return pd.DataFrame(data)
    except:
        return None

def analyze_w_bottom(code):
    df = get_stock_df(code)
    # 若資料不足直接跳過，減少後續運算
    if df is None or len(df) < 20: return None
    
    close = df['close'].values
    volume = df['capacity'].values
    
    # 計算最低點與成交量平均 (直接在 numpy 數組上操作，比 DataFrame 快)
    min_price = min(close[-20:])
    avg_volume = sum(volume[-20:]) / 20
    
    # 邏輯判斷：收盤價符合底 + 成交量放大
    if abs(close[-1] - min_price) / min_price < 0.05 and volume[-1] > (avg_volume * 1.2):
        return f"✅ 疑似 W 底 (收:{close[-1]})"
    return None

# UI 介面
all_industry = sorted(list(set([twstock.codes[c].group for c in twstock.codes if twstock.codes[c].group != '0'])))
selected_industry = st.selectbox("請選擇產業：", all_industry)

if st.button("🚀 啟動閃電掃描"):
    target_list = [code for code, info in twstock.codes.items() if info.group == selected_industry]
    
    # 顯示總共要掃幾檔
    st.write(f"正在掃描 {len(target_list)} 檔股票...")
    
    # 將進度條與掃描結合
    progress_bar = st.progress(0)
    results = []
    
    # 使用 ThreadPoolExecutor 並設定 max_workers=10 榨乾頻寬
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_code = {executor.submit(analyze_w_bottom, code): code for code in target_list}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_code)):
            res = future.result()
            if res:
                results.append({"代碼": future_to_code[future], "狀態": res})
            progress_bar.progress((i + 1) / len(target_list))
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.info("該產業目前無符合條件標的。")
