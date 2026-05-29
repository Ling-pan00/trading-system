import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
# 🚀 引入手機端網頁相容性最強、免伺服器字型包的 HTML5 專業 K 線套件
from streamlit_echarts import st_echarts

# ==========================================
# 1. 系統初始化與手機網頁配置
# ==========================================
st.set_page_config(page_title="12大科技核心股選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技與機電核心股：AI 選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📱 手機無痛相容・正宗紅綠 K 線版")

# 記憶池：維持快取，避免手機點擊選單時重算
if 'all_stock_cache' not in st.session_state:
    st.session_state.all_stock_cache = {}  
if 'final_report_df' not in st.session_state:
    st.session_state.final_report_df = None

# 精選 30 檔最活躍的台股核心科技與重電代表股
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
# 2. 核心大批量大數據下載通道
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    targets = get_verified_pool()
    st.session_state.all_stock_cache = {} 
    st.session_state.final_report_df = None
    
    start_dt = (today_tw - timedelta(days=120)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 正在批量同步 Yahoo 盤後 K 線數據..."):
        try:
            df_raw = yf.download(tickers=targets, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
            
            if df_raw.empty:
                st.error("❌ Yahoo 伺服器拒絕連線，請稍後重試。")
            else:
                rows = []
                success_count = 0
                
                for s_id in targets:
                    if s_id in df_raw.columns.levels[0]:
                        df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                        if len(df_stock) < 40: continue
                            
                        df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                        df_stock = df_stock.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                        
                        # 計算均線技術指標
                        df_stock['MA5'] = df_stock['Close'].rolling(5).mean()
                        df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                        
                        st.session_state.all_stock_cache[s_id] = df_stock
                        success_count += 1
                        
                        last = df_stock.iloc[-1]
                        prev = df_stock.iloc[-2]
                        
                        # 多頭排列核心策略：收盤大於月線
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
                                'AI 預估波段勝率': f"{score}%", 
                                'sort_key': abs(dist)
                            })
                            
                if rows:
                    st.session_state.final_report_df = pd.DataFrame(rows).sort_values('sort_key').drop(columns=['sort_key'])
                else:
                    st.session_state.final_report_df = pd.DataFrame()
                    
                st.success(f"🎉 掃描完成！成功解析出 {success_count} 檔核心股數據！")
        except Exception as e:
            st.error(f"❌ 發生系統錯誤: {str(e)}")

# ==========================================
# 3. 🎯 畫面呈現：【選項與真正紅綠 K 線完全置頂】
# ==========================================
if st.session_state.final_report_df is not None:
    
    # 決定下拉選單要有哪些股票
    if st.session_state.final_report_df.empty:
        active_list = list(st.session_state.all_stock_cache.keys())
    else:
        active_list = st.session_state.final_report_df['股票代碼'].tolist()
        
    if active_list:
        st.markdown("---")
        st.subheader("📱 手機看圖優先區 (請直接使用下方選單切換個股)")
        st.info("💡 溫馨提示：請不要點擊最底下的表格。手指直接點擊下方這個「下拉選單」就能換股票看真正的 K 線圖！")
        
        # 👑 唯一的連動核心機關
        user_pick = st.selectbox(
            "👉 請點擊這裡切換股票代碼：", 
            options=active_list, 
            index=0
        )
        
        if user_pick in st.session_state.all_stock_cache:
            st.markdown(f"### 📊 **{user_pick}** 正宗紅綠 K 線圖 (含 5MA/20MA)")
            
            # 取最近 50 天的 K 線，大小在手機直式螢幕上最精美、好讀
            df_target = st.session_state.all_stock_cache[user_pick].tail(50).copy()
            
            # 轉換為 ECharts 專用的格式
            dates_list = pd.to_datetime(df_target['Date']).dt.strftime('%m/%d').tolist()
            
            # K線基礎數據格式為: [開盤價, 收盤價, 最低價, 最高價]
            k_values = df_target[['Open', 'Close', 'Low', 'High']].values.tolist()
            ma5_list = [round(v, 2) if not pd.isna(v) else None for v in df_target['MA5'].tolist()]
            ma20_list = [round(v, 2) if not pd.isna(v) else None for v in df_target['MA20'].tolist()]
            
            # 🛠️ 終極黑科技：利用 ECharts 純前端 Canvas 渲染，在手機內建網頁裡永不隱形
            echarts_options = {
                "backgroundColor": "#121212", # 暗黑系風格
                "legend": {
                    "data": ["K線", "5MA", "20MA"], 
                    "textStyle": {"color": "#ffffff"},
                    "top": "2%"
                },
                "tooltip": {
                    "trigger": "axis", 
                    "axisPointer": {"type": "cross"},
                    "backgroundColor": "rgba(30, 30, 30, 0.9)",
                    "textStyle": {"color": "#fff"}
                },
                "grid": {"left": "12%", "right": "8%", "bottom": "15%", "top": "15%"},
                "xAxis": {
                    "type": "category", 
                    "data": dates_list, 
                    "axisLine": {"lineStyle": {"color": "#777777"}},
                    "axisLabel": {"color": "#ffffff"}
                },
                "yAxis": {
                    "scale": True, 
                    "axisLine": {"lineStyle": {"color": "#777777"}}, 
                    "splitLine": {"lineStyle": {"color": "#222222"}},
                    "axisLabel": {"color": "#ffffff"}
                },
                "series": [
                    {
                        "name": "K線",
                        "type": "candlestick",
                        "data": k_values,
                        # 🎯 嚴格遵循台股市場習慣：紅漲綠跌
                        "itemStyle": {
                            "color": "#ef5350",       # 紅色實體 (收盤 >= 開盤)
                            "color0": "#26a69a",      # 綠色實體 (收盤 < 開盤)
                            "borderColor": "#ef5350",   # 紅色外框
                            "borderColor0": "#26a69a"  # 綠色外框
                        }
                    },
                    {
                        "name": "5MA", 
                        "type": "line", 
                        "data": ma5_list, 
                        "smooth": True, 
                        "lineStyle": {"opacity": 0.8, "color": "#ffeb3b", "width": 1.5}
                    },
                    {
                        "name": "20MA", 
                        "type": "line", 
                        "data": ma20_list, 
                        "smooth": True, 
                        "lineStyle": {"opacity": 0.8, "color": "#e040fb", "width": 2}
                    }
                ]
            }
            
            # 在網頁上渲染出 400 像素高、觸控流暢的實體 K 線圖
            st_echarts(options=echarts_options, height="400px")
            
            # 數據看板區
            curr_data = df_target.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("今日收盤價", f"${round(curr_data['Close'], 2)}")
            m2.metric("5MA 均價", f"${round(curr_data['MA5'], 2)}")
            m3.metric("20MA 月線", f"${round(curr_data['MA20'], 2)}")

    # 歷史清單表格放在最底下作為對照參考
    st.markdown("---")
    st.subheader("📋 今日 AI 多頭貼線選股對照清單 (僅供參考)")
    if st.session_state.final_report_df.empty:
        st.warning("ℹ️ 今日盤後無完全符合強勢貼線的多頭核心股。")
    else:
        st.dataframe(st.session_state.final_report_df, use_container_width=True)
