import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
from streamlit_echarts import st_echarts
import requests

# ==========================================
# 1. 系統初始化與手機網頁配置
# ==========================================
st.set_page_config(page_title="台股 11 大產業核心選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 台股 11 大產業大數據：AI 選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📱 全產業自動同步・正宗紅綠 K 線版")

# 記憶池
if 'all_stock_cache' not in st.session_state:
    st.session_state.all_stock_cache = {}  
if 'final_report_df' not in st.session_state:
    st.session_state.final_report_df = None

# ==========================================
# 2. 【高穩定 OpenAPI 機制】自動抓取 11 大產業上市櫃全名單
# ==========================================
def get_industry_stock_pool():
    """直接從證交所/櫃買官方 OpenAPI 串流抓取指定 11 個產業的股票代碼 (無快取殘留)"""
    target_industries = {
        "電機機械", "化學工業", "半導體業", "電腦及週邊設備業", "電腦週邊", 
        "光電業", "通信網路業", "通信網路", "電子零組件業", "電子組件", 
        "電子通路業", "電子通路", "資訊服務業", "資訊服務", "其他電子業", 
        "其他電子", "數位雲端"
    }
    
    pool = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 1. 抓取上市股票總表 (透過 OpenAPI)
    try:
        twse_url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
        res = requests.get(twse_url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                ind = item.get('產業別', '').strip()
                code = item.get('公司代號', '').strip()
                # 篩選產業別並排除權證、存託憑證(代碼大於4碼或含英文字)
                if any(t in ind for t in target_industries) and len(code) == 4 and code.isdigit():
                    pool.append(f"{code}.TW")
    except Exception as e:
        st.error(f"⚠️ 上市 OpenAPI 連線失敗: {str(e)}")

    # 2. 抓取上櫃股票總表 (透過櫃買 OpenAPI)
    try:
        tpex_url = "https://www.tpex.org.tw/openapi/v1/t187ap03_O"
        res = requests.get(tpex_url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                ind = item.get('產業別', '').strip()
                code = item.get('公司代號', '').strip()
                if any(t in ind for t in target_industries) and len(code) == 4 and code.isdigit():
                    pool.append(f"{code}.TWO")
    except Exception as e:
        st.error(f"⚠️ 上櫃 OpenAPI 連線失敗: {str(e)}")
        
    return sorted(list(set(pool)))

# ==========================================
# 3. 核心大批量大數據下載通道
# ==========================================
total_pool = get_industry_stock_pool()

if not total_pool:
    st.error("❌ 無法從官方伺服器取得任何股票名單，請確認網路或稍後重試。")
else:
    st.write(f"📊 **目前監控守備範圍**：精選 11 大指定產業，共計 **{len(total_pool)}** 檔個股。")

    if st.button(f"🏛️ 啟動 {len(total_pool)} 檔全產業即時盤後掃描", type="primary", use_container_width=True):
        st.session_state.all_stock_cache = {} 
        st.session_state.final_report_df = None
        
        start_dt = (today_tw - timedelta(days=120)).strftime("%Y-%m-%d")
        end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("🚀 正在進行跨產業大批量 K 線數據同步與 AI 策略計算..."):
            try:
                # 採用 Yahoo 大批量分組下載
                df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
                
                if df_raw.empty:
                    st.error("❌ Yahoo 伺服器拒絕連線或未回傳數據，請稍後重試。")
                else:
                    rows = []
                    success_count = 0
                    has_multi_index = isinstance(df_raw.columns, pd.MultiIndex)
                    
                    for idx, s_id in enumerate(total_pool):
                        progress_bar.progress((idx + 1) / len(total_pool))
                        
                        try:
                            if has_multi_index:
                                if s_id not in df_raw.columns.levels[0]: continue
                                df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                            else:
                                df_stock = df_raw.dropna(subset=['Close']).reset_index()
                                
                            if len(df_stock) < 40: continue
                                
                            df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                            df_stock = df_stock.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                            
                            df_stock['MA5'] = df_stock['Close'].rolling(5).mean()
                            df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                            
                            st.session_state.all_stock_cache[s_id] = df_stock
                            success_count += 1
                            
                            last = df_stock.iloc[-1]
                            prev = df_stock.iloc[-2]
                            
                            if last['Close'] > last['MA20']:
                                dist = (last['Close'] - last['MA5']) / last['MA5']
                                
                                # 🎯 【精準回檔區間：股價距離 5 日線 -2% 到 +3% 之間】
                                if -0.02 <= dist <= 0.03:
                                    score = 60
                                    if last['Volume'] > prev['Volume']: score += 20
                                    score += 20
                                    
                                    rows.append({
                                        '股票代碼': s_id, 
                                        '今日收盤': round(last['Close'], 2), 
                                        '月線(20MA)': round(last['MA20'], 2),
                                        '偏離5MA 幅度': f"{round(dist * 100, 2)}%", 
                                        'AI 預估波段勝率': f"{score}%", 
                                        'sort_key': abs(dist)
                                    })
                        except:
                            continue
                                
                    if rows:
                        st.session_state.final_report_df = pd.DataFrame(rows).sort_values('sort_key').drop(columns=['sort_key'])
                    else:
                        st.session_state.final_report_df = pd.DataFrame()
                        
                    status_text.success(f"🎉 11大產業掃描完成！成功解析出 {success_count} 檔有效股票！")
            except Exception as e:
                st.error(f"❌ 發生系統錯誤: {str(e)}")

# ==========================================
# 4. 🎯 畫面呈現：【選項與真正紅綠 K 線完全置頂】
# ==========================================
if st.session_state.final_report_df is not None:
    
    if st.session_state.final_report_df.empty:
        active_list = list(st.session_state.all_stock_cache.keys())
    else:
        active_list = st.session_state.final_report_df['股票代碼'].tolist()
        
    if active_list:
        st.markdown("---")
        st.subheader("📱 手機看圖優先區 (請直接使用下方選單切換個股)")
        st.info("💡 溫馨提示：手指直接點擊下方這個「下拉選單」就能隨時換股票看 K 線圖！")
        
        user_pick = st.selectbox(
            "👉 請點擊這裡切換股票代碼：", 
            options=active_list, 
            index=0
        )
        
        if user_pick in st.session_state.all_stock_cache:
            st.markdown(f"### 📊 **{user_pick}** 正宗紅綠 K 線圖 (含 5MA/20MA)")
            
            df_target = st.session_state.all_stock_cache[user_pick].tail(50).copy()
            dates_list = pd.to_datetime(df_target['Date']).dt.strftime('%m/%d').tolist()
            
            k_values = df_target[['Open', 'Close', 'Low', 'High']].values.tolist()
            ma5_list = [round(v, 2) if not pd.isna(v) else None for v in df_target['MA5'].tolist()]
            ma20_list = [round(v, 2) if not pd.isna(v) else None for v in df_target['MA20'].tolist()]
            
            echarts_options = {
                "backgroundColor": "#121212", 
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
                        "itemStyle": {
                            "color": "#ef5350",       
                            "color0": "#26a69a",      
                            "borderColor": "#ef5350",   
                            "borderColor0": "#26a69a"  
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
            
            st_echarts(options=echarts_options, height="400px")
            
            curr_data = df_target.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("今日收盤價", f"${round(curr_data['Close'], 2)}")
            m2.metric("5MA 均價", f"${round(curr_data['MA5'], 2)}")
            m3.metric("20MA 月線", f"${round(curr_data['MA20'], 2)}")

    # 歷史清單表格放在最底下作為對照參考
    st.markdown("---")
    st.subheader("📋 今日 AI 多頭貼線選股對照清單 (僅供參考)")
    if st.session_state.final_report_df.empty:
        st.warning("ℹ️ 今日盤後無完全符合強勢貼線(-2% ~ +3%)的多頭核心股。")
    else:
        st.dataframe(st.session_state.final_report_df, use_container_width=True)
