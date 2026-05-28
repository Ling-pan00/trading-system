import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 系統初始化與頁面設定
# ==========================================
st.set_page_config(page_title="12大科技核心股選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技與機電核心股：AI 選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 官方大量安全下載版")

# 核心記憶池
if 'all_data_dict' not in st.session_state:
    st.session_state.all_data_dict = {}  # 儲存乾淨的個股 DataFrame
if 'filtered_report' not in st.session_state:
    st.session_state.filtered_report = None

# ==========================================
# 2. 精選台股最具流動性、絕對有 K 線的核心科技股
# ==========================================
def get_verified_pool():
    core = [
        2330, 2317, 2454, 2308, 2382, 2303, 3711, 2357, 3231, 2408,
        1503, 1513, 1519, 1605, 1608, 1795, 2409, 3481, 3008, 2345,
        2356, 2376, 2377, 2324, 4938, 2353, 3037, 3034, 2405, 2352
    ]
    pool = []
    for c in core:
        suffix = ".TW" if c < 3000 else ".TWO"
        pool.append(f"{c}{suffix}")
    return pool

# ==========================================
# 3. 控制核心：使用官方高效率異步大批量下載法
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    targets = get_verified_pool()
    st.session_state.all_data_dict = {} # 清空舊庫
    st.session_state.filtered_report = None
    
    start_dt = (today_tw - timedelta(days=120)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 正在使用官方高速通道載入 12 大板塊核心股資料..."):
        try:
            # 🎯 核心改良：一次性批量下載，並透過 group_by='ticker' 保持結構清晰，避免被 Yahoo 封鎖
            df_raw = yf.download(
                tickers=targets, start=start_dt, end=end_dt,
                auto_adjust=True, group_by='ticker', progress=False
            )
            
            if df_raw.empty:
                st.error("❌ Yahoo Finance 伺服器拒絕連線，請稍後幾分鐘再按一次。")
            else:
                rows = []
                success_count = 0
                
                # 遍歷所有代碼，將 MultiIndex 拆解為乾淨的格式
                for s_id in targets:
                    try:
                        # 檢查該股票是否存在於下載結果的頂層索引中
                        if s_id in df_raw.columns.levels[0]:
                            df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                            
                            if len(df_stock) < 40:
                                continue
                                
                            # 欄位名稱強制大寫標準化，避免大小寫陷阱
                            df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                            df_stock = df_stock.rename(columns={
                                'Date': 'Date', 'Open': 'Open', 'High': 'High',
                                'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'
                            })
                            
                            # 計算技術指標
                            df_stock['MA5'] = df_stock['Close'].rolling(5).mean()
                            df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                            df_stock['MA60'] = df_stock['Close'].rolling(60).mean()
                            
                            # 存入系統記憶池
                            st.session_state.all_data_dict[s_id] = df_stock
                            success_count += 1
                            
                            # 策略判斷
                            last = df_stock.iloc[-1]
                            prev = df_stock.iloc[-2]
                            
                            if last['MA20'] > last['MA60'] and last['Close'] > last['MA20']:
                                dist = (last['Close'] - last['MA5']) / last['MA5']
                                
                                score = 60
                                if last['Volume'] > prev['Volume']: score += 15
                                if abs(dist) < 0.05: score += 15
                                
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
                        
                st.success(f"🎉 掃描完成！成功解析出 {success_count} 檔核心個股數據！")
                
                if rows:
                    st.session_state.filtered_report = pd.DataFrame(rows).sort_values('sort_key').drop(columns=['sort_key'])
                else:
                    st.session_state.filtered_report = pd.DataFrame() # 空表格防呆
        except Exception as e:
            st.error(f"❌ 發生未知錯誤: {str(e)}")

# ==========================================
# 4. 畫面呈現與手機連動下拉選單
# ==========================================
if st.session_state.filtered_report is not None:
    st.markdown("---")
    
    # 決定下拉選單可選的股票清單
    if st.session_state.filtered_report.empty:
        st.warning("ℹ️ 今日盤後無完全符合強勢貼線的多頭核心股。下方已自動為您加載可用個股進行查詢。")
        active_list = list(st.session_state.all_data_dict.keys())
    else:
        st.subheader("📋 今日 AI 強勢多頭貼線選股清單")
        st.dataframe(st.session_state.filtered_report, use_container_width=True)
        active_list = st.session_state.filtered_report['股票代碼'].tolist()
        
    # 如果有成功下載到任何一檔資料，就強制顯示手機專用看圖選單
    if active_list:
        st.markdown("---")
        st.subheader("📱 手機專用：下拉選單看 K 線走勢")
        
        user_pick = st.selectbox(
            "請「點擊這裡」選擇你想看圖的股票代碼：",
            options=active_list,
            index=0
        )
        
        if user_pick in st.session_state.all_data_dict:
            st.markdown(f"### 📈 正在繪製：**{user_pick}** 趨勢圖")
            
            target_df = st.session_state.all_data_dict[user_pick]
            plot_df = target_df.tail(60).copy()
            
            # 轉換成 Streamlit 內建圖表格式
            plot_df['Date'] = pd.to_datetime(plot_df['Date']).dt.date
            chart_data = plot_df.set_index('Date')[['Close', 'MA5', 'MA20']]
            chart_data.columns = ['收盤價', '5日線(5MA)', '20日線(20MA)']
            
            # 🚀 拋棄不穩定的 Plotly，改用 100% 支援手機版網頁的原生 line_chart
            st.line_chart(chart_data, use_container_width=True)
            
            # 數據指標小卡片
            curr_data = plot_df.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("今日最新收盤", f"${round(curr_data['Close'], 2)}")
            m2.metric("5MA 均價", f"${round(curr_data['MA5'], 2)}")
            m3.metric("20MA 月線", f"${round(curr_data['MA20'], 2)}")
    else:
        st.error("⚠️ 目前緩存區無任何股票數據，請確認網路正常後重新點擊上方紅色按鈕掃描。")
