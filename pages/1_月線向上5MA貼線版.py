import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 網頁初始化與外觀設定
# ==========================================
st.set_page_config(page_title="12大科技核心股選股系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 12大科技核心股：AI 輕量選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📱 手機無痛內置圖表版")

# 初始化 Session 記憶池
if 'all_stocks_data' not in st.session_state:
    st.session_state.all_stocks_data = {}  
if 'display_report' not in st.session_state:
    st.session_state.display_report = None

def get_verified_pool():
    # 嚴選 30 檔科技與重電機電核心權值股
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
# 2. 核心大批量下載與計算引擎
# ==========================================
if st.button("🏛️ 啟動 12 大科技板塊即時盤後掃描", type="primary", use_container_width=True):
    targets = get_verified_pool()
    st.session_state.all_stocks_data = {} 
    st.session_state.display_report = None
    
    start_dt = (today_tw - timedelta(days=90)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 正在大批量安全載入核心股 K 線資料..."):
        try:
            df_raw = yf.download(tickers=targets, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
            
            if df_raw.empty:
                st.error("❌ Yahoo Finance 伺服器拒絕連線，請稍後重試。")
            else:
                rows = []
                success_count = 0
                
                for s_id in targets:
                    if s_id in df_raw.columns.levels[0]:
                        df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index()
                        if len(df_stock) < 30: continue
                            
                        df_stock.columns = [str(c).strip().title() for c in df_stock.columns]
                        df_stock = df_stock.rename(columns={'Date': 'Date', 'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'})
                        
                        # 計算月線
                        df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                        
                        st.session_state.all_stocks_data[s_id] = df_stock
                        success_count += 1
                        
                        last = df_stock.iloc[-1]
                        
                        # 多頭策略：收盤價大於月線
                        if last['Close'] > last['MA20']:
                            # 🎯 核心秘密武器：抓取最近 20 天的收盤價，變成一個 List 清單，準備塞進表格
                            recent_trend = df_stock['Close'].tail(20).tolist()
                            
                            rows.append({
                                '股票代碼': s_id,
                                '今日收盤': round(last['Close'], 2),
                                '月線(20MA)': round(last['MA20'], 2),
                                '近20日趨勢': recent_trend  # 這是一整串價格數據
                            })
                            
                if rows:
                    st.session_state.display_report = pd.DataFrame(rows)
                else:
                    st.session_state.display_report = pd.DataFrame()
                    
                st.success(f"🎉 掃描完成！成功解析出 {success_count} 檔核心個股！")
        except Exception as e:
            st.error(f"❌ 發生未知錯誤: {str(e)}")

# ==========================================
# 3. 畫面呈現區：【100% 絕對看得到走勢的黑科技表格】
# ==========================================
if st.session_state.display_report is not None:
    st.markdown("---")
    
    if st.session_state.display_report.empty:
        st.warning("ℹ️ 今日盤後無符合多頭排列個股。")
    else:
        st.subheader("📋 今日 AI 多頭選股清單（內置趨勢線版）")
        st.info("💡 提示：走勢圖已直接嵌在表格最右邊！在手機上完全不卡頓、絕對不會隱形！")
        
        # 🚀 終極神盾：利用 Streamlit 內建 column_config 直接把圖表塞進表格裡
        st.data_editor(
            st.session_state.display_report,
            column_config={
                "股票代碼": st.column_config.TextColumn("股票代碼", help="個股代號"),
                "今日收盤": st.column_config.NumberColumn("今日收盤", format="$%.2f"),
                "月線(20MA)": st.column_config.NumberColumn("月線(20MA)", format="$%.2f"),
                # 👑 就是這行！把陣列直接變成表格內微型折線圖，手機瀏覽器 100% 支援
                "近20日趨勢": st.column_config.LineChartColumn(
                    "近20日波段趨勢",
                    y_min=None,
                    y_max=None
                )
            },
            disabled=True, # 唯讀模式，防止誤觸修改
            use_container_width=True,
            hide_index=True
        )
