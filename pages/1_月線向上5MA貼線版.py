import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
# 🚀 引進手機端渲染最強大的正宗 K 線庫
from streamlit_echarts import st_echarts

# ==========================================
# 1. 初始化與設定
# ==========================================
st.set_page_config(page_title="12大科技核心股選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技核心股：AI 專業選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📊 正宗紅綠 K 線手機特製版")

if 'all_data' not in st.session_state:
    st.session_state.all_data = {}  
if 'report_df' not in st.session_state:
    st.session_state.report_df = None

def get_verified_pool():
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
# 2. 數據下載
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    targets = get_verified_pool()
    st.session_state.all_data = {} 
    st.session_state.report_df = None
    
    start_dt = (today_tw - timedelta(days=120)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 數據載入中..."):
        try:
            df_raw = yf.download(tickers=targets, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
            
            if df_raw.empty:
                st.error("❌ 下載失敗，請稍後重試。")
            else:
                rows = []
                success_count = 0
                
                for s_id in targets:
                    if s_id in df_raw.columns.levels[0]:
                        df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                        if len(df_stock) < 30: continue
                            
                        df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                        df_stock = df_stock.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                        
                        df_stock['MA5'] = df_stock['Close'].rolling(5).mean()
                        df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                        
                        st.session_state.all_data[s_id] = df_stock
                        success_count += 1
                        
                        last = df_stock.iloc[-1]
                        if last['Close'] > last['MA20']:
                            dist = (last['Close'] - last['MA5']) / last['MA5']
                            rows.append({
                                '股票代碼': s_id, '今日收盤': round(last['Close'], 2), '月線(20MA)': round(last['MA20'], 2), 'sort_key': abs(dist)
                            })
                            
                if rows:
                    st.session_state.report_df = pd.DataFrame(rows).sort_values('sort_key').drop(columns=['sort_key'])
                else:
                    st.session_state.report_df = pd.DataFrame()
                    
                st.success(f"🎉 成功載入 {success_count} 檔核心股數據！")
        except Exception as e:
            st.error(f"系統錯誤: {str(e)}")

# ==========================================
# 3. 畫面呈現：正宗紅綠 K 線區 (選單置頂)
# ==========================================
if st.session_state.report_df is not None:
    
    active_list = st.session_state.report_df['股票代碼'].tolist() if not st.session_state.report_df.empty else list(st.session_state.all_data.keys())
        
    if active_list:
        st.markdown("---")
        st.subheader("📱 手機看圖區 (請使用下方選單切換個股)")
        
        user_pick = st.selectbox("👉 請點擊這裡切換股票代碼：", options=active_list, index=0)
        
        if user_pick in st.session_state.all_data:
            df_target = st.session_state.all_data[user_pick].tail(50).copy() # 取50天最適合手機閱讀
            
            # 準備 ECharts 格式的數據
            dates = pd.to_datetime(df_target['Date']).dt.strftime('%m/%d').tolist()
            
            # ECharts 的 K 線格式為: [開盤, 收盤, 最低, 最高]
            k_values = df_target[['Open', 'Close', 'Low', 'High']].values.tolist()
            ma5_values = [round(v, 2) if not pd.isna(v) else None for v in df_target['MA5'].tolist()]
            ma20_values = [round(v, 2) if not pd.isna(v) else None for v in df_target['MA20'].tolist()]
            
            # 💡 核心黑科技：用純前端 JavaScript 配置一個帶有均線、正宗台股紅漲綠跌的 K 線圖
            options = {
                "backgroundColor": "#151515",
                "legend": {"data": ["K線", "5MA", "20MA"], "textStyle": {"color": "#fff"}},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}},
                "grid": {"left": "10%", "right": "10%", "bottom": "15%"},
                "xAxis": {"type": "category", "data": dates, "axisLine": {"lineStyle": {"color": "#888"}}},
                "yAxis": {"scale": True, "axisLine": {"lineStyle": {"color": "#888"}}, "splitLine": {"lineStyle": {"color": "#333"}}},
                "series": [
                    {
                        "name": "K線",
                        "type": "candlestick",
                        "data": k_values,
                        # 🎯 符合台灣市場習慣：紅漲綠跌
                        "itemStyle": {
                            "color": "#ef5350",       # 紅色收紅
                            "color0": "#26a69a",      # 綠色收黑
                            "borderColor": "#ef5350",
                            "borderColor0": "#26a69a"
                        }
                    },
                    {"name": "5MA", "type": "line", "data": ma5_values, "smooth": True, "lineStyle": {"opacity": 0.7, "color": "#ffeb3b"}},
                    {"name": "20MA", "type": "line", "data": ma20_values, "smooth": True, "lineStyle": {"opacity": 0.7, "color": "#e040fb"}}
                ]
            }
            
            # 噴出正宗 K 線，高度 400px 最適合手機直式觀看
            st_echarts(options=options, height="400px")
            
            # 數值小卡片
            curr = df_target.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("今日收盤", f"${round(curr['Close'], 2)}")
            m2.metric("5MA均線", f"${round(curr['MA5'], 2)}")
            m3.metric("20MA月線", f"${round(curr['MA20'], 2)}")

    st.markdown("---")
    st.subheader("📋 盤後選股對照清單")
    st.dataframe(st.session_state.report_df, use_container_width=True)
