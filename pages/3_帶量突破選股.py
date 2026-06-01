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
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 策略：20日新高 + 2倍增量")

# Session State 管理
if 'breakout_report_df' not in st.session_state:
    st.session_state.breakout_report_df = None

# ==========================================
# 2. 核心股票池 (簡化版，建議保持精簡以避免 Yahoo 拒絕請求)
# ==========================================
def get_industry_stock_pool():
    # 這裡放入你的股票代碼清單
    return ["2330.TW", "2454.TW", "2317.TW", "2303.TW", "3008.TW", "2382.TW", "3231.TW"]

total_pool = get_industry_stock_pool()
st.write(f"📊 **帶量突破雷達**：目前監控 {len(total_pool)} 檔核心標的。")

# ==========================================
# 3. 數據下載與運算邏輯
# ==========================================
if st.button("🚀 啟動強勢帶量突破掃描", type="primary"):
    start_dt = (today_tw - timedelta(days=60)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("正在同步 20 日量價模型..."):
        # 使用 threads 加速，避免一次過多請求導致斷線
        df_raw = yf.download(total_pool, start=start_dt, end=end_dt, group_by='ticker', threads=True)
        
        results = []
        
        for s_id in total_pool:
            try:
                # 處理 yfinance 不同版本回傳的 MultiIndex 結構
                if isinstance(df_raw.columns, pd.MultiIndex):
                    df_stock = df_raw[s_id].dropna(subset=['Close'])
                else:
                    df_stock = df_raw.dropna(subset=['Close'])
                
                if len(df_stock) < 22:
                    continue
                
                # 計算策略指標
                df_stock['MA20_Vol'] = df_stock['Volume'].rolling(window=20).mean()
                df_stock['High20'] = df_stock['High'].rolling(window=20).max().shift(1)
                
                last = df_stock.iloc[-1]
                
                # 策略條件：今日收盤創 20 日新高 AND 今日量 > 2 倍 20 日均量
                if last['Close'] > last['High20'] and last['Volume'] > (last['MA20_Vol'] * 2):
                    results.append({
                        "代碼": s_id,
                        "收盤價": round(last['Close'], 2),
                        "成交量": int(last['Volume']),
                        "均量": int(last['MA20_Vol'])
                    })
            except Exception as e:
                continue
        
        if results:
            st.success(f"掃描完成！發現 {len(results)} 檔符合策略標的：")
            st.dataframe(pd.DataFrame(results))
        else:
            st.warning("目前無標的符合帶量突破條件。")
