import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go

# ==========================================
# 1. 系統基本設定與網頁初始化
# ==========================================
st.set_page_config(page_title="12大核心科技股即時篩選系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技與機電核心股：即時 AI 選股系統")
st.caption(f"目前台北時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 環境：極速手機優化版")

st.info("🎯 **當前監控產業**：電機機械、電器電纜、化學工業、半導體業、電腦週邊、光電業、通信網路、電子組件、電子通路、資訊服務、其他電子、數位雲端。")

# 🔥 核心記憶池初始化：確保任何重新整理、點擊按鈕，資料都穩如泰山
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'raw_df_all' not in st.session_state:
    st.session_state.raw_df_all = None  
if 'mobile_selected_stock' not in st.session_state:
    st.session_state.mobile_selected_stock = None  

# ==========================================
# 2. 核心功能：台股 12 大科技/機電板塊官方實體股白名單
# ==========================================
def get_all_tw_stocks():
    stocks = [
        # 電機機械與電器電纜
        1503, 1504, 1513, 1514, 1519, 1521, 1522, 1524, 1525, 1526, 1527, 1530, 1531, 1532, 1533, 1535, 1536, 1537, 
        1538, 1539, 1541, 1558, 1560, 1582, 1583, 1589, 1590, 1592, 1597, 1603, 1604, 1605, 1608, 1609, 1611, 1612, 
        1615, 1616, 1617, 1618, 1625, 
        # 化學工業
        1704, 1710, 1711, 1712, 1713, 1714, 1717, 1718, 1721, 1722, 1723, 1725, 1727, 1730, 1732, 1735, 1742, 1750, 
        1773, 1776, 1783, 1786, 1789, 1795, 
        # 半導體核心群
        2302, 2303, 2329, 2330, 2337, 2338, 2344, 2351, 2363, 2369, 2379, 2388, 2408, 2434, 2436, 2441, 2449, 2454, 
        2458, 2481, 3006, 3016, 3034, 3035, 3041, 3054, 3189, 3228, 3231, 3260, 3264, 3289, 3374, 3413, 3438, 3529, 
        3532, 3545, 3557, 3567, 3583, 3588, 3592, 3653, 3661, 3680, 3686, 3707, 4919, 4952, 4961, 4967, 4968, 5269, 
        5274, 5347, 5471, 5483, 6138, 6147, 6182, 6223, 6239, 6243, 6257, 6271, 6411, 6415, 6435, 6451, 6462, 6477, 
        6488, 6510, 6515, 6525, 6531, 6533, 6548, 6568, 6573, 6670, 6679, 6684, 6719, 6756, 6770, 6811, 8016, 8028, 
        8054, 8081, 8261, 8271, 8299, 
        # 電腦週邊、光電、通信網路
        2312, 2313, 2314, 2317, 2323, 2324, 2345, 2352, 2353, 2356, 2357, 2360, 2362, 2364, 2365, 2376, 2377, 2382, 
        2393, 2395, 2397, 2405, 2406, 2409, 2412, 2417, 2419, 2421, 2424, 2425, 2439, 2444, 2450, 2455, 2457, 2474, 
        2480, 2482, 2484, 2485, 2489, 2495, 2496, 2498, 3005, 3008, 3013, 3017, 3019, 3021, 3022, 3023, 3024, 3026, 
        3027, 3030, 3031, 3032, 3037, 3044, 3045, 3046, 3047, 3048, 3049, 3050, 3051, 3055, 3057, 3059, 3060, 3062, 
        3071, 3090, 3094, 3130, 3149, 3211, 3213, 3217, 3218, 3238, 3296, 3305, 3308, 3311, 3312, 3321, 3338, 3356, 
        3362, 3363, 3376, 3380, 3406, 3437, 3443, 3450, 3454, 3481, 3494, 3501, 3504, 3515, 3518, 3526, 3528, 3533, 
        3535, 3536, 3540, 3550, 3563, 3576, 3591, 3593, 3596, 3605, 3607, 3609, 3615, 3617, 3622, 3624, 3630, 3652, 
        3665, 3669, 3673, 3682, 3694, 4904, 4906, 4912, 4915, 4916, 4934, 4935, 4938, 4942, 4943, 4956, 4958, 4960, 
        4976, 4977, 5215, 5234, 5245, 5258, 5288, 5371, 5388, 5410, 5425, 5457, 5469, 5493, 6112, 6116, 6120, 6125, 
        6136, 6139, 6141, 6142, 6143, 6152, 6153, 6164, 6166, 6168, 6176, 6189, 6196, 6205, 6206, 6213, 6214, 6217, 
        6220, 6224, 6230, 6235, 6245, 6251, 6269, 6277, 6278, 6281, 6283, 6285, 6405, 6412, 6414, 6416, 6426, 6442, 
        6443, 6449, 6470, 6491, 6541, 6550, 6558, 6664, 6668, 6669, 6672, 6674, 6682, 6695, 6698, 8011, 8021, 8027, 
        8033, 8039, 8046, 8050, 8059, 8069, 8070, 8072, 8086, 8103, 8104, 8105, 8110, 8112, 8114, 8147, 8150, 8163, 
        8210, 8213, 8215, 8249, 8255, 8289, 8358, 8410, 8431, 9914, 9921, 9945, 9955
    ]
    
    stock_pool = []
    for code in sorted(list(set(stocks))):
        s_code = str(code)
        if code < 3000 or (3700 <= code < 4900) or code in [6116, 6269, 6669]:
            stock_pool.append(f"{s_code}.TW")
        else:
            stock_pool.append(f"{s_code}.TWO")
            
    return list(set(stock_pool))

# ==========================================
# 3. 量化指標運算 
# ==========================================
def calculate_indicators_and_signals(all_data):
    processed_list = []
    for stock_id, df in all_data.groupby('Stock_ID'):
        if len(df) < 65:
            continue
        df = df.copy().sort_values('Date')
        
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        df['Bias_20'] = (df['Close'] - df['MA20']) / df['MA20']
        df['Dist_5MA'] = (df['Close'] - df['MA5']) / df['MA5']
        
        trend_score = np.where(df['MA20'] > df['MA60'], 0.6, 0.4)
        bias_score = np.where(df['Bias_20'].abs() < 0.1, 0.15, 0.05)
        vol_score = np.where(df['Volume'] > df['Volume'].rolling(5).mean(), 0.1, 0.05)
        
        df['AI_Win_Rate'] = trend_score + bias_score + vol_score
        processed_list.append(df.tail(1))
        
    if not processed_list:
        return pd.DataFrame()
    return pd.concat(processed_list, ignore_index=True)

# ==========================================
# 4. 策略篩選器
# ==========================================
def filter_strategy(df_today, tolerance=0.08):
    if df_today.empty:
        return pd.DataFrame()
    
    condition_trend = (df_today['MA20'] > df_today['MA60']) & (df_today['Close'] > df_today['MA20'])
    condition_near_5ma = df_today['Dist_5MA'].abs() <= tolerance
    
    filtered = df_today[condition_trend & condition_near_5ma]
    return filtered.sort_values('AI_Win_Rate', ascending=False)

# ==========================================
# 5. Streamlit 控制與下載邏輯 (點擊後只管把資料塞進記憶池)
# ==========================================
st.sidebar.header("⚙️ 篩選設定")
m_tolerance = st.sidebar.slider("5MA 貼近容忍度 (±%)", 1, 15, 8) / 100

if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary"):
    with st.spinner("🚀 正在大範圍巡檢 12 大板塊官方實體股..."):
        raw_stock_pool = get_all_tw_stocks()
        start_dt = (today_tw - timedelta(days=120)).strftime("%Y-%m-%d")
        end_dt = today_tw.strftime("%Y-%m-%d")
        
        batch_size = 50
        all_frames = []
        
        st.info(f"🧬 已載入 12 大板塊共 {len(raw_stock_pool)} 檔實體股。開始安全分流掃描...")
        progress_text = st.empty()
        p_bar = st.progress(0)
        chunks = [raw_stock_pool[i:i + batch_size] for i in range(0, len(raw_stock_pool), batch_size)]
        
        for idx, chunk in enumerate(chunks):
            progress_text.text(f"📥 正在下載第 {idx+1} / {len(chunks)} 個科技股區段...")
            p_bar.progress((idx + 1) / len(chunks))
            try:
                df_chunk_raw = yf.download(
                    tickers=chunk, start=start_dt, end=end_dt, 
                    auto_adjust=True, group_by='ticker', progress=False, timeout=15
                )
                if df_chunk_raw.empty: 
                    continue
                    
                if isinstance(df_chunk_raw.columns, pd.MultiIndex):
                    for stock_id in chunk:
                        if stock_id in df_chunk_raw.columns.levels[0]:
                            df_k = df_chunk_raw[stock_id].dropna(subset=['Close', 'Volume']).reset_index()
                            if len(df_k) >= 60:
                                df_k['Stock_ID'] = stock_id
                                all_frames.append(df_k)
            except Exception:
                continue
        
        progress_text.text("✅ K 線數據載入成功，正在執行量化模型運算...")
        
        if not all_frames:
            st.error("❌ 下載失敗，請稍後再試。")
        else:
            df_all = pd.concat(all_frames, ignore_index=True)
            if 'Date' not in df_all.columns and 'index' in df_all.columns:
                df_all = df_all.rename(columns={'index': 'Date'})
                
            # 灌入全域池
            st.session_state.raw_df_all = df_all
            df_today_signals = calculate_indicators_and_signals(df_all)
            df_filtered = filter_strategy(df_today_signals, tolerance=m_tolerance)
            st.session_state.scan_results = df_filtered
            
            if not df_filtered.empty:
                st.session_state.mobile_selected_stock = str(df_filtered.iloc[0]['Stock_ID'])

# ==========================================
# 6. 獨立渲染區 (只要記憶池有資料，不管怎麼點按鈕，它都必定畫圖)
# ==========================================
if st.session_state.scan_results is not None:
    st.markdown("---")
    st.subheader(f"📋 12大核心板塊：今日 AI 多頭貼線選股清單")
    
    if st.session_state.scan_results.empty:
        st.warning(f"ℹ️ 當前篩選條件下無符合條件的科技股。")
    else:
        # 1. 建立乾淨的代碼對照表
        candidate_list = [str(x) for x in st.session_state.scan_results['Stock_ID'].tolist()]
        
        # 2. 呈現數據表格
        display_df = st.session_state.scan_results[['Stock_ID', 'Close', 'MA20', 'Dist_5MA', 'AI_Win_Rate']].copy()
        display_df['Dist_5MA'] = (display_df['Dist_5MA'] * 100).round(2).astype(str) + "%"
        display_df['AI_Win_Rate'] = (display_df['AI_Win_Rate'] * 100).round(1).astype(str) + "%"
        display_df['Close'] = display_df['Close'].round(2)
        display_df['MA20'] = display_df['MA20'].round(2)
        display_df.columns = ['股票代碼', '今日收盤價', '月線(20MA)', '偏離5MA幅度', 'AI 預估波段勝率']
        st.dataframe(display_df, use_container_width=True)

        # 3. 手機專用按鈕區
        st.markdown("---")
        st.subheader("📱 手機專用：點擊下方按鈕看日 K 線圖")
        
        display_buttons = candidate_list[:15]
        
        # 確保預設一定有選中一檔
        if st.session_state.mobile_selected_stock not in display_buttons and display_buttons:
            st.session_state.mobile_selected_stock = display_buttons[0]
            
        cols = st.columns(3)
        for idx, s_id in enumerate(display_buttons):
            col_target = cols[idx % 3]
            is_active = (s_id == st.session_state.mobile_selected_stock)
            btn_type = "primary" if is_active else "secondary"
            
            # 🔥 關鍵改良：點擊按鈕時，直接修改 State，並立刻 rerun 讓下方圖表重畫
            if col_target.button(f"📊 {s_id}", key=f"btn_{s_id}", type=btn_type, use_container_width=True):
                st.session_state.mobile_selected_stock = s_id
                st.rerun()
                
        # 4. 繪製 K 線圖區
        current_view_stock = st.session_state.mobile_selected_stock
            
        if current_view_stock and st.session_state.raw_df_all is not None:
            st.markdown(f"### 📈 正在檢視日 K 線：**{current_view_stock}**")
            
            stock_k_data = st.session_state.raw_df_all[st.session_state.raw_df_all['Stock_ID'] == current_view_stock].sort_values('Date')
            plot_df = stock_k_data.tail(90)
            
            if not plot_df.empty:
                fig_k = go.Figure()
                fig_k.add_trace(go.Candlestick(
                    x=plot_df['Date'], open=plot_df['Open'], high=plot_df['High'], low=plot_df['Low'], close=plot_df['Close'], name='日 K 線',
                    increasing_line_color='#FF3333', decreasing_line_color='#00AA00'
                ))
                
                # 在畫圖時動態補上均線，不影響記憶體
                plot_df = plot_df.copy()
                plot_df['MA5'] = plot_df['Close'].rolling(window=5).mean()
                plot_df['MA20'] = plot_df['Close'].rolling(window=20).mean()
                plot_df['MA60'] = plot_df['Close'].rolling(window=60).mean()
                
                fig_k.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['MA5'], name='5MA', line=dict(color='#FFDD00', width=1.5)))
                fig_k.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['MA20'], name='20MA', line=dict(color='#FF00FF', width=2)))
                fig_k.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['MA60'], name='60MA', line=dict(color='#00FFFF', width=1.5)))
                
                fig_k.update_layout(
                    template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                    margin=dict(l=10, r=10, t=20, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_k, use_container_width=True)
