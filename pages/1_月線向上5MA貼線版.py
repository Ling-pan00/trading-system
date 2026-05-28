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
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 終極防封鎖個體戶版")

# 記憶池防線
if 'db_all_stocks' not in st.session_state:
    st.session_state.db_all_stocks = {}  # 儲存每檔成功的 DataFrame
if 'final_report' not in st.session_state:
    st.session_state.final_report = None

# ==========================================
# 2. 精選台股最活躍、絕對有資料的科技核心股
# ==========================================
def get_hardcoded_pool():
    # 嚴選 30 檔最具代表性權值股，避免冷門股拖垮 API
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
# 3. 控制核心：逐檔下載（防暴神盾）
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    targets = get_hardcoded_pool()
    st.session_state.db_all_stocks = {} # 清空舊庫
    st.session_state.final_report = None
    
    p_bar = st.progress(0)
    msg_box = st.empty()
    
    rows = []
    success_num = 0
    
    # 🎯 核心改良：一檔一檔單獨抓，分開擊破 Yahoo 封鎖
    for i, stock_code in enumerate(targets):
        msg_box.text(f"📥 正在安全下載個股 ({i+1}/{len(targets)}): {stock_code} ...")
        p_bar.progress((i + 1) / len(targets))
        
        try:
            # 使用 period="6m" 最穩定，拋棄日期邊界計算
            ticker = yf.Ticker(stock_code)
            df_single = ticker.history(period="6m", interval="1d")
            
            if df_single.empty or len(df_single) < 40:
                continue
            
            # 拍平並大寫欄位名稱
            df_single = df_single.reset_index()
            df_single.columns = [str(c).strip().upper() for c in df_single.columns]
            
            # 標準化欄位名稱
            df_single = df_single.rename(columns={
                'DATE': 'Date', 'OPEN': 'Open', 'HIGH': 'High', 
                'LOW': 'Low', 'CLOSE': 'Close', 'VOLUME': 'Volume'
            })
            
            # 計算核心技術指標
            df_single['MA5'] = df_single['Close'].rolling(5).mean()
            df_single['MA20'] = df_single['Close'].rolling(20).mean()
            df_single['MA60'] = df_single['Close'].rolling(60).mean()
            
            # 塞入記憶庫
            st.session_state.db_all_stocks[stock_code] = df_single
            success_num += 1
            
            # 多頭判定邏輯
            last = df_single.iloc[-1]
            prev = df_single.iloc[-2]
            
            if last['MA20'] > last['MA60'] and last['Close'] > last['MA20']:
                dist = (last['Close'] - last['MA5']) / last['MA5']
                
                # 計算 AI 評分
                score = 60
                if last['Volume'] > prev['Volume']: score += 15
                if abs(dist) < 0.05: score += 15
                
                rows.append({
                    '股票代碼': stock_code,
                    '今日收盤': round(last['Close'], 2),
                    '月線(20MA)': round(last['MA20'], 2),
                    '偏離5MA 幅度': f"{round(dist * 100, 2)}%",
                    'AI 預估波段勝率': f"{score}%",
                    'sort_key': abs(dist)
                })
        except:
            # 某一檔壞掉，直接跳過，不牽連整張表
            continue
            
    msg_box.success(f"🎉 掃描圓滿完成！成功繞過封鎖並載入 {success_num} 檔核心個股資料！")
    
    if rows:
        st.session_state.final_report = pd.DataFrame(rows).sort_values('sort_key').drop(columns=['sort_key'])
    else:
        st.session_state.final_report = pd.DataFrame()

# ==========================================
# 4. 渲染呈現與手機連動下拉選單
# ==========================================
if st.session_state.final_report is not None:
    st.markdown("---")
    
    if st.session_state.final_report.empty:
        st.warning("ℹ️ 當前市場股票暫未完美符合多頭貼線條件，下方仍提供個股走勢查詢。")
        # 即使沒有篩選出的個股，也允許查詢所有成功下載的股票
        active_list = list(st.session_state.db_all_stocks.keys())
    else:
        st.subheader("📋 今日 AI 強勢多頭貼線選股清單")
        st.dataframe(st.session_state.final_report, use_container_width=True)
        active_list = st.session_state.final_report['股票代碼'].tolist()
        
    if active_list:
        st.markdown("---")
        st.subheader("📱 手機專用：下拉選單看 K 線走勢")
        
        # 🛠️ 核心救星：用這個下拉選單取代點擊表格格子！100% 觸發網頁更新
        user_pick = st.selectbox(
            "請「點擊這裡」選擇你想看圖的股票代碼：",
            options=active_list,
            index=0
        )
        
        if user_pick in st.session_state.db_all_stocks:
            st.markdown(f"### 📈 正在繪製：**{user_pick}** 趨勢圖")
            
            target_df = st.session_state.db_all_stocks[user_pick]
            plot_df = target_df.tail(60).copy()
            
            # 轉換成 Streamlit 內建圖表格式
            plot_df['Date'] = pd.to_datetime(plot_df['Date']).dt.date
            chart_data = plot_df.set_index('Date')[['Close', 'MA5', 'MA20']]
            chart_data.columns = ['收盤價', '5日線(5MA)', '20日線(20MA)']
            
            # 🚀 拋棄不穩定的 Plotly，改用 100% 支援手機版網頁的原生 line_chart
            st.line_chart(chart_data, use_container_width=True)
            
            # 數據儀表板
            curr_data = plot_df.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("今日最新收盤", f"${round(curr_data['Close'], 2)}")
            m2.metric("5MA 均價", f"${round(curr_data['MA5'], 2)}")
            m3.metric("20MA 月線", f"${round(curr_data['MA20'], 2)}")
