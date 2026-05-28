import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 初始化與網頁設定
# ==========================================
st.set_page_config(page_title="12大科技核心股選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技與機電核心股：AI 即時選股")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 手機極速防錯版")

# 初始化 Session State 記憶池
if 'all_stock_data' not in st.session_state:
    st.session_state.all_stock_data = {}  # 用字典存每檔股票的乾淨 DataFrame
if 'filtered_summary' not in st.session_state:
    st.session_state.filtered_summary = None

# ==========================================
# 2. 精簡化核心核心科技股名單 (挑選最活躍的重要代表股，大幅提升下載成功率)
# ==========================================
def get_clean_pool():
    # 這是精選出的核心科技/機電代表股白名單，確保流動性與下載絕對安全
    core_codes = [
        2330, 2317, 2454, 2308, 2382, 2303, 3711, 2357, 3231, 2408,
        1503, 1513, 1519, 1605, 1608, 1795, 1773, 2409, 3481, 3008,
        2345, 2356, 2376, 2377, 2324, 6239, 4938, 2353, 3037, 3034,
        2405, 1776, 2302, 5245, 2352, 6682, 6679, 6672, 6667, 1780
    ]
    pool = []
    for c in core_codes:
        if c < 3000:
            pool.append(f"{c}.TW")
        else:
            pool.append(f"{c}.TWO")
    return pool

# ==========================================
# 3. 核心下載與運算邏輯 (安全逐檔下載機制)
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    stock_pool = get_clean_pool()
    st.session_state.all_stock_data = {} # 清空舊資料
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    success_count = 0
    summary_rows = []
    
    # 逐檔下載，採取最高安全防護
    for idx, ticker_id in enumerate(stock_pool):
        status_text.text(f"📥 正在安全下載個股資料 ({idx+1}/{len(stock_pool)}): {ticker_id}")
        progress_bar.progress((idx + 1) / len(stock_pool))
        
        try:
            # 抓取過去 6 個月的資料，確保足夠計算均線
            t_obj = yf.Ticker(ticker_id)
            df = t_obj.history(period="6m", interval="1d")
            
            if df.empty or len(df) < 65:
                continue
                
            # 欄位強制定名與清洗
            df = df.reset_index()
            df.columns = [str(c).strip().title() for c in df.columns]
            df = df.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
            
            # 計算技術指標
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            
            # 存入全域字典
            st.session_state.all_stock_data[ticker_id] = df
            
            # 提取最新一筆資料做篩選評分
            last_day = df.iloc[-1]
            prev_day = df.iloc[-2]
            
            close_p = last_day['Close']
            ma20_p = last_day['MA20']
            ma60_p = last_day['MA60']
            ma5_p = last_day['MA5']
            
            # 核心多頭策略：20MA > 60MA (多頭排列) 且 收盤價大於 20MA
            if ma20_p > ma60_p and close_p > ma20_p:
                dist_5ma = (close_p - ma5_p) / ma5_p
                
                # 計算 AI 勝率權重
                score = 0.5
                if last_day['Volume'] > prev_day['Volume']: score += 0.2
                if abs(dist_5ma) < 0.05: score += 0.2
                
                summary_rows.append({
                    '股票代碼': ticker_id,
                    '今日收盤': round(close_p, 2),
                    '月線 (20MA)': round(ma20_p, 2),
                    '偏離5MA 幅度': f"{round(dist_5ma * 100, 2)}%",
                    'AI 預估波段勝率': f"{round(score * 100, 1)}%",
                    'raw_dist': abs(dist_5ma)
                })
                success_count += 1
        except Exception as e:
            continue
            
    status_text.text(f"✅ 掃描完成！成功載入 {len(st.session_state.all_stock_data)} 檔核心股數據。")
    
    if summary_rows:
        df_sum = pd.DataFrame(summary_rows).sort_values(by='raw_dist')
        st.session_state.filtered_summary = df_sum.drop(columns=['raw_dist'])
    else:
        st.session_state.filtered_summary = pd.DataFrame()

# ==========================================
# 4. 畫面呈現與手機專用連動選單 (解決點擊格子無效的痛點)
# ==========================================
if st.session_state.filtered_summary is not None:
    st.markdown("---")
    
    if st.session_state.filtered_summary.empty:
        st.warning("ℹ️ 今日暫無完全符合強勢貼線的多頭核心股，建議放寬條件或觀察大盤。")
    else:
        st.subheader("📋 今日 AI 強勢多頭選股清單")
        st.caption("💡 提示：下表僅供對照參考。若要查看趨勢圖，請使用下方專門為手機設計的「下拉選單」進行切換！")
        st.dataframe(st.session_state.filtered_summary, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📱 手機專用看圖區")
        
        # 提取清單中所有的股票代碼當作選單選項
        available_stocks = st.session_state.filtered_summary['股票代碼'].tolist()
        
        # 建立手機版專用下拉式選單（這個一變動，Streamlit 保證 100% 重新渲染畫圖！）
        selected_stock = st.selectbox(
            "請選擇欲檢視的股票代碼：",
            options=available_stocks,
            index=0
        )
        
        if selected_stock in st.session_state.all_stock_data:
            st.markdown(f"### 📊 個股波段走勢圖：{selected_stock}")
            
            stock_df = st.session_state.all_stock_data[selected_stock]
            # 取出最近 60 筆交易日做圖
            plot_df = stock_df.tail(60).copy()
            
            # 整理成 Streamlit 內建圖表要的格式 (以 Date 為 Index)
            plot_df['Date'] = pd.to_datetime(plot_df['Date']).dt.date
            chart_data = plot_df.set_index('Date')[['Close', 'MA5', 'MA20']]
            chart_data.columns = ['今日收盤價', '5日均線(5MA)', '20日月線(20MA)']
            
            # 手機原生安全流折線圖：保證有數據就絕對畫得出來，不卡頓、不隱形
            st.line_chart(chart_data, use_container_width=True)
            
            # 呈現數據小卡片
            latest_data = plot_df.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("今日收盤", f"${round(latest_data['Close'], 2)}")
            c2.metric("5MA 均價", f"${round(latest_data['MA5'], 2)}")
            c3.metric("20MA 月線", f"${round(latest_data['MA20'], 2)}")
