import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 網頁初始化設定
# ==========================================
st.set_page_config(page_title="12大科技核心股選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技與機電核心股：AI 選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📱 手機選單連動優化版")

# 初始化記憶池，確保下載完的資料可以一直留著
if 'cached_data' not in st.session_state:
    st.session_state.cached_data = {}  # 存股票日 K 資料
if 'summary_table' not in st.session_state:
    st.session_state.summary_table = None

# 精選 30 檔最活躍的台股核心科技與重電代表股
def get_core_pool():
    core = [
        2330, 2317, 2454, 2308, 2382, 2303, 3711, 2357, 3231, 2408,
        1503, 1504, 1513, 1514, 1519, 1605, 1608, 1795, 2409, 3481,
        3008, 2345, 2356, 2376, 2377, 2324, 4938, 2353, 3037, 3034
    ]
    pool = []
    for c in core:
        suffix = ".TW" if c < 3000 else ".TWO"
        pool.append(f"{c}{suffix}")
    return pool

# ==========================================
# 2. 數據下載引擎 (使用最高相容性的批量下載)
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    targets = get_core_pool()
    st.session_state.cached_data = {} 
    st.session_state.summary_table = None
    
    start_dt = (today_tw - timedelta(days=120)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 正在安全載入板塊核心股 K 線資料..."):
        try:
            df_raw = yf.download(tickers=targets, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
            
            if df_raw.empty:
                st.error("❌ 讀取失敗，請稍後再試。")
            else:
                rows = []
                success_count = 0
                
                for s_id in targets:
                    if s_id in df_raw.columns.levels[0]:
                        df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                        if len(df_stock) < 40: continue
                        
                        df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                        df_stock = df_stock.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                        
                        # 計算均線
                        df_stock['MA5'] = df_stock['Close'].rolling(5).mean()
                        df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                        df_stock['MA60'] = df_stock['Close'].rolling(60).mean()
                        
                        st.session_state.cached_data[s_id] = df_stock
                        success_count += 1
                        
                        last = df_stock.iloc[-1]
                        prev = df_stock.iloc[-2]
                        
                        # 多頭篩選策略
                        if last['Close'] > last['MA20']:
                            dist = (last['Close'] - last['MA5']) / last['MA5']
                            score = 60
                            if last['Volume'] > prev['Volume']: score += 20
                            if abs(dist) < 0.05: score += 20
                            
                            rows.append({
                                '股票代碼': s_id,
                                '今日收盤': round(last['Close'], 2),
                                '月線(20MA)': round(last['MA20'], 2),
                                '偏離5MA 幅度': f"{round(dist * 100, 2)}%",
                                'AI 預估勝率': f"{score}%",
                                'sort_key': abs(dist)
                            })
                
                if rows:
                    st.session_state.summary_table = pd.DataFrame(rows).sort_values('sort_key').drop(columns=['sort_key'])
                else:
                    st.session_state.summary_table = pd.DataFrame()
                    
                st.success(f"🎉 掃描完成！成功載入 {success_count} 檔核心個股數據！")
        except Exception as e:
            st.error(f"❌ 系統發生錯誤: {str(e)}")

# ==========================================
# 3. 畫面呈現與【真正的下拉選單看圖機制】
# ==========================================
if st.session_state.summary_table is not None:
    st.markdown("---")
    
    # 決定選單內有哪些股票可以選
    if st.session_state.summary_table.empty:
        st.warning("ℹ   今日盤後無完全符合貼線條件的個股，下方已自動為您加載全部個股以供查詢。")
        active_list = list(st.session_state.cached_data.keys())
    else:
        st.subheader("📋 今日 AI 多頭貼線選股清單")
        st.dataframe(st.session_state.summary_table, use_container_width=True)
        active_list = st.session_state.summary_table['股票代碼'].tolist()
        
    # 🎯 終極救星：只要資料庫有股票，就強行渲染出「手機下拉選單」
    if active_list:
        st.markdown("---")
        st.subheader("📱 手機專用：切換下方選單看趨勢圖")
        st.info("💡 核心提示：請不要點擊上方表格內的個股！請點選下方這個「下拉式選單」來切換你要看的股票！")
        
        # 這是唯一的互動機關，點它才會真正連動
        chosen_stock = st.selectbox(
            "👉 請點擊這裡選擇你想看圖的股票：",
            options=active_list,
            index=0
        )
        
        if chosen_stock in st.session_state.cached_data:
            st.markdown(f"### 📈 **{chosen_stock}** 趨勢走勢圖")
            
            plot_df = st.session_state.cached_data[chosen_stock].tail(60).copy()
            plot_df['Date'] = pd.to_datetime(plot_df['Date']).dt.date
            
            # 整理圖表數據
            chart_data = plot_df.set_index('Date')[['Close', 'MA5', 'MA20']]
            chart_data.columns = ['收盤價', '5日均線(5MA)', '20日月線(20MA)']
            
            # 使用 100% 支援手機瀏覽器的原生圖表
            st.line_chart(chart_data, use_container_width=True)
            
            # 數據儀表板小卡片
            latest_data = plot_df.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("今日最新收盤", f"${round(latest_data['Close'], 2)}")
            m2.metric("5MA 均價", f"${round(latest_data['MA5'], 2)}")
            m3.metric("20MA 月線", f"${round(latest_data['MA20'], 2)}")
