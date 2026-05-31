import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from streamlit_echarts import st_echarts

# ==========================================
# 1. 頁面基本配置與時區
# ==========================================
st.set_page_config(page_title="全市場帶量突破選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("⚡ 策略四：強勢帶量突破箱體選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📱 全市場動態掃描 + 參數自由配")

# 獨立的 Session 記憶池
if 'breakout_stock_cache' not in st.session_state:
    st.session_state.breakout_stock_cache = {}  
if 'breakout_report_df' not in st.session_state:
    st.session_state.breakout_report_df = None

# ==========================================
# 2. 🎛️ 側邊欄：自由調整箱型整理參數
# ==========================================
st.sidebar.header("⚙️ 突破策略參數微調")

st.sidebar.markdown("### 🔷 價格突破天數")
n_high_days = st.sidebar.slider(
    "1. 股價創幾日新高：", 
    min_value=5, max_value=60, value=20, step=5,
    help="原本為20日。尋找突破過去 N 天盤整高點的標的。"
)

st.sidebar.markdown("### 🔷 主力增量倍數")
volume_ratio_threshold = st.sidebar.slider(
    "2. 成交量爆發倍數：", 
    min_value=1.2, max_value=4.0, value=2.0, step=0.1,
    help="原本為2.0倍。今日成交量需大於均量的 N 倍。"
)

st.sidebar.markdown("### 🔷 箱體壓縮洗盤特徵")
compress_days = st.sidebar.slider(
    "3. 箱體壓縮檢視天數：", 
    min_value=5, max_value=20, value=10, step=1,
    help="原本為10日。檢視突破前，過去這幾天是否處於洗盤期。"
)

amplitude_threshold = st.sidebar.slider(
    "4. 箱體洗盤振幅限制 (%)：", 
    min_value=5, max_value=25, value=10, step=1,
    help="原本為10%。在這段盤整期間內，最高價與最低價的落差。股性活潑的中小型股（如6584）建議調高至 12%~15% 試試。"
)
# 轉換為小數點以利計算
amplitude_limit = amplitude_threshold / 100.0


# ==========================================
# 3. 🌐 全市場上市櫃股票池動態獲取
# ==========================================
@st.cache_data(ttl=86400) # 快取 24 小時，避免重複對證交所造成負擔
def get_full_market_pool():
    try:
        # 動態爬取證交所最新上市公司清單 (普通股)
        twse_url = 'https://isin.twse.com.tw/isin/C_public.jsp?strMode=2'
        df_twse = pd.read_html(twse_url)[0]
        df_twse.columns = df_twse.iloc[0]
        df_twse = df_twse.iloc[1:]
        
        twse_codes = []
        for item in df_twse['有價證券代號及名稱'].astype(str):
            parts = item.split('\u3000') # 全形空白分隔
            if len(parts) >= 1 and len(parts[0].strip()) == 4 and parts[0].strip().isdigit():
                twse_codes.append(f"{parts[0].strip()}.TW")
                
        # 動態爬取櫃買中心最新上櫃公司清單 (普通股)
        tpex_url = 'https://isin.twse.com.tw/isin/C_public.jsp?strMode=4'
        df_tpex = pd.read_html(tpex_url)[0]
        df_tpex.columns = df_tpex.iloc[0]
        df_tpex = df_tpex.iloc[1:]
        
        tpex_codes = []
        for item in df_tpex['有價證券代號及名稱'].astype(str):
            parts = item.split('\u3000')
            if len(parts) >= 1 and len(parts[0].strip()) == 4 and parts[0].strip().isdigit():
                tpex_codes.append(f"{parts[0].strip()}.TWO")
                
        full_pool = sorted(list(set(twse_codes + tpex_codes)))
        return full_pool
    except Exception as e:
        st.error(f"⚠️ 動態抓取全市場清單失敗：{e}。系統自動啟動基礎備份股票池。")
        # 應急用的備份核心池（確保程式不崩潰，並包含你想測試的 6584）
        return ["2330.TW", "2317.TW", "2454.TW", "6584.TWO", "1513.TW", "1503.TW", "3037.TW", "2303.TW"]

total_pool = get_full_market_pool()
st.write(f"📊 **帶量突破雷達範圍**：動態追蹤台灣全市場 **{len(total_pool)}** 檔上市與上櫃股票（已全面包含 6584 南俊國際 等所有標的）。")


# ==========================================
# 4. 🎯 全市場大數據下載與動態突破演算法
# ==========================================
if st.button(f"⚡ 啟動全市場 {len(total_pool)} 檔強勢帶量突破全面掃描", type="primary", use_container_width=True):
    st.session_state.breakout_stock_cache = {} 
    st.session_state.breakout_report_df = None
    
    # 根據選定的參數自動回推所需天數，並多抓 25 天作為均線與假日的緩衝
    safety_days = max(n_high_days, compress_days) + 25
    start_dt = (today_tw - timedelta(days=safety_days)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    rows = []
    success_count = 0
    
    with st.spinner("🚀 正在執行全市場大數據同步與自訂箱體壓縮濾網過濾..."):
        # 由於全市場高達上千檔，為避免記憶體溢出，採取分批（每批 100 檔）下載與解析
        batch_size = 100
        for b_idx in range(0, len(total_pool), batch_size):
            batch_pool = total_pool[b_idx: b_idx + batch_size]
            
            # 更新進度條與文字
            current_progress = min((b_idx + batch_size) / len(total_pool), 1.0)
            progress_bar.progress(current_progress)
            status_text.text(f"⏳ 正在掃描全市場個股： 第 {b_idx} ~ {min(b_idx + batch_size, len(total_pool))} 檔...")
            
            try:
                df_raw = yf.download(tickers=batch_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
                if df_raw.empty: continue
                
                has_multi_index = isinstance(df_raw.columns, pd.MultiIndex)
                
                for s_id in batch_pool:
                    try:
                        if has_multi_index:
                            if s_id not in df_raw.columns.levels[0]: continue
                            df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                        else:
                            df_stock = df_raw.dropna(subset=['Close']).reset_index()
                            
                        # 檢查資料長度是否足夠計算使用者設定的天數
                        if len(df_stock) < (max(n_high_days, compress_days) + 2): continue
                            
                        df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                        df_stock = df_stock.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                        
                        # 【動態調整】計算 20 日均量 (維持傳統 20 日作為主力均量基準)
                        df_stock['Vol_MA20'] = df_stock['Volume'].rolling(20).mean()
                        
                        st.session_state.breakout_stock_cache[s_id] = df_stock
                        success_count += 1
                        
                        # 取出今日與歷史切片
                        last = df_stock.iloc[-1]
                        
                        # 根據側邊欄設定，動態切出對應的歷史天數（不含今天）
                        past_high_days = df_stock.tail(n_high_days + 1).iloc[:-1]
                        past_compress_days = df_stock.tail(compress_days + 1).iloc[:-1]
                        
                        # 【條件一】股價創 N 日新高 (今天收盤價 > 過去 N 天的最高收盤價)
                        high_n_day = past_high_days['Close'].max()
                        if last['Close'] > high_n_day:
                            
                            # 【條件二】當日成交量大於 20 日均量的倍數 (使用滑桿設定的值)
                            if last['Volume'] > (last['Vol_MA20'] * volume_ratio_threshold):
                                
                                # 【條件三】過去 M 天橫盤洗盤特徵：振幅(最高/最低差距) < 自訂%
                                max_p = past_compress_days['High'].max()
                                min_p = past_compress_days['Low'].min()
                                amplitude_calc = (max_p - min_p) / min_p
                                
                                if amplitude_calc < amplitude_limit:
                                    vol_ratio = last['Volume'] / last['Vol_MA20']
                                    
                                    rows.append({
                                        '股票代碼': s_id,
                                        '今日收盤': round(last['Close'], 2),
                                        f'{n_high_days}日最高': round(high_n_day, 2),
                                        '今日成交量': int(last['Volume']),
                                        '20日均量': int(last['Vol_MA20']),
                                        '爆量倍數': f"{round(vol_ratio, 2)}倍",
                                        f'{compress_days}日洗盤振幅': f"{round(amplitude_calc * 100, 2)}%",
                                        'sort_key': vol_ratio # 以爆量倍數由高到低排序
                                    })
                    except:
                        continue
            except:
                continue
                
        if rows:
            st.session_state.breakout_report_df = pd.DataFrame(rows).sort_values('sort_key', ascending=False).drop(columns=['sort_key'])
        else:
            st.session_state.breakout_report_df = pd.DataFrame()
            
        status_text.success(f"🎉 全市場突破雷達掃描完成！成功比對全台灣 {success_count} 檔上市櫃個股！")

# ==========================================
# 5. 🎯 手機與桌面畫面呈現
# ==========================================
if st.session_state.breakout_report_df is not None:
    
    if st.session_state.breakout_report_df.empty:
        # 如果今日沒有完全符合的個股，預設抓取前 20 檔有下載成功的股票提供圖表切換
        active_list = list(st.session_state.breakout_stock_cache.keys())[:20]
    else:
        active_list = st.session_state.breakout_report_df['股票代碼'].tolist()
        
    if active_list:
        st.markdown("---")
        st.subheader("📱 強勢突破・手機看圖優先區")
        
        user_pick = st.selectbox(
            "👉 請選擇帶量表態個股（已依爆量強度排序）：", 
            options=active_list, 
            index=0
        )
        
        if user_pick in st.session_state.breakout_stock_cache:
            st.markdown(f"### 📊 **{user_pick}** 帶量動能 K 線圖")
            
            df_target = st.session_state.breakout_stock_cache[user_pick].tail(40).copy()
            dates_list = pd.to_datetime(df_target['Date']).dt.strftime('%m/%d').tolist()
            
            k_values = df_target[['Open', 'Close', 'Low', 'High']].values.tolist()
            
            echarts_options = {
                "backgroundColor": "#121212", 
                "legend": {"data": ["K線"], "textStyle": {"color": "#ffffff"}, "top": "2%"},
                "tooltip": {"trigger": "axis", "axisPointer": {"type": "cross"}, "backgroundColor": "rgba(30, 30, 30, 0.9)", "textStyle": {"color": "#fff"}},
                "grid": {"left": "12%", "right": "8%", "bottom": "15%", "top": "15%"},
                "xAxis": {"type": "category", "data": dates_list, "axisLine": {"lineStyle": {"color": "#777777"}}, "axisLabel": {"color": "#ffffff"}},
                "yAxis": {"scale": True, "axisLine": {"lineStyle": {"color": "#777777"}}, "splitLine": {"lineStyle": {"color": "#222222"}}, "axisLabel": {"color": "#ffffff"}},
                "series": [
                    {"name": "K線", "type": "candlestick", "data": k_values, "itemStyle": {"color": "#ef5350", "color0": "#26a69a", "borderColor": "#ef5350", "borderColor0": "#26a69a"}}
                ]
            }
            st_echarts(options=echarts_options, height="400px")
            
            curr_data = df_target.iloc[-1]
            m1, m2 = st.columns(2)
            m1.metric("今日收盤價", f"${round(curr_data['Close'], 2)}")
            m2.metric("今日成交量", f"{int(curr_data['Volume']):,}")

    st.markdown("---")
    st.subheader("📋 橫盤洗盤突破・全市場黑馬對照清單")
    if st.session_state.breakout_report_df.empty:
        st.warning(f"ℹ️ 全市場今日暫無完全符合「{compress_days}日洗盤振幅 < {amplitude_threshold}%、爆量創 {n_high_days} 日新高」的個股。中小型飆股（如南俊國際）往往洗盤幅度較大，請試著將左側邊欄的『箱體洗盤振幅限制』調寬至 12%~15% 後，再次點擊按鈕掃描！")
    else:
        st.dataframe(st.session_state.breakout_report_df, use_container_width=True)
