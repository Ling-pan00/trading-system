import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 頁面基本配置
# ==========================================
st.set_page_config(page_title="帶量突破選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("⚡ 策略四：強勢帶量突破箱體選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 20日新高 + 2倍增量")

if 'breakout_stock_cache' not in st.session_state:
    st.session_state.breakout_stock_cache = {}  
if 'breakout_report_df' not in st.session_state:
    st.session_state.breakout_report_df = None

# ==========================================
# 2. 股票池定義
# ==========================================
def get_industry_stock_pool():
    # 這裡放您的股票清單
    full_pool = ["2330.TW", "2454.TW", "2317.TW", "2303.TW", "3008.TW"] 
    return sorted(list(set(full_pool)))

# ==========================================
# 3. 核心運算邏輯
# ==========================================
total_pool = get_industry_stock_pool()

st.write(f"📊 **帶量突破雷達範圍**：精選 {len(total_pool)} 檔標的。")

if st.button("⚡ 啟動選股掃描", type="primary"):
    st.session_state.breakout_stock_cache = {} 
    
    start_dt = (today_tw - timedelta(days=60)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    progress_bar = st.progress(0)
    
    with st.spinner("🚀 正在處理大數據..."):
        try:
            # 下載數據
            df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
            
            if df_raw.empty:
                st.error("❌ 無數據返回，請檢查網路或股票代碼。")
            else:
                results = []
                for i, s_id in enumerate(total_pool):
                    progress_bar.progress((i + 1) / len(total_pool))
                    
                    # 處理 MultiIndex 格式
                    if isinstance(df_raw.columns, pd.MultiIndex):
                        if s_id not in df_raw.columns.levels[0]:
                            continue
                        df_stock = df_raw[s_id].dropna(subset=['Close'])
                    else:
                        df_stock = df_raw.dropna(subset=['Close'])
                    
                    if len(df_stock) < 22:
                        continue
                    
                    # 簡單範例邏輯：判斷最新收盤價是否創新高
                    last_close = df_stock['Close'].iloc[-1]
                    high_20 = df_stock['Close'].iloc[-21:-1].max()
                    
                    if last_close > high_20:
                        results.append({"代碼": s_id, "收盤價": round(float(last_close), 2)})
                
                if results:
                    st.success(f"掃描完成！發現 {len(results)} 檔標的。")
                    st.table(pd.DataFrame(results))
                else:
                    st.info("今日無符合條件的標的。")
                    
        except Exception as e:
            st.error(f"系統錯誤: {e}")
