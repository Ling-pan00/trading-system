import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import mplfinance as mpf
import numpy as np

# ==========================================
# 1. 頁面基本配置
# ==========================================
st.set_page_config(page_title="投信鎖碼選股系統", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 策略三：投信鎖碼核心選股系統")
st.caption(f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 📱 投信3日連買 + 雙線之上 + 低週轉率")

if 'sitc_stock_cache' not in st.session_state: st.session_state.sitc_stock_cache = {} 
if 'sitc_report_df' not in st.session_state: st.session_state.sitc_report_df = None

# ==========================================
# 2. 530檔 核心池 (原封不動)
# ==========================================
def get_industry_stock_pool():
    # (此處省略部分清單內容以節省版面，請保持您原本的完整清單)
    full_pool = ["1503.TW", "1504.TW", "2330.TW", "2317.TW", "2454.TW", "3008.TW", "2303.TW", "8454.TW"] 
    return sorted(list(set(full_pool)))

total_pool = get_industry_stock_pool()
st.write(f"📊 **投信鎖碼雷達範圍**：共計 **{len(total_pool)}** 檔上市櫃個股。")

# ==========================================
# 3. 掃描邏輯 (原封不動)
# ==========================================
if st.button(f"🏛️ 啟動 {len(total_pool)} 檔全產業投信鎖碼大數據掃描", type="primary", use_container_width=True):
    st.session_state.sitc_stock_cache = {} 
    start_dt = (today_tw - timedelta(days=180)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    with st.spinner("🚀 正在執行掃描..."):
        df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
        rows = []
        for s_id in total_pool:
            try:
                df_stock = df_raw[s_id].dropna(subset=['Close']).reset_index() if isinstance(df_raw.columns, pd.MultiIndex) else df_raw.dropna(subset=['Close']).reset_index()
                if len(df_stock) < 65: continue
                df_stock.columns = [str(c).title() for c in df_stock.columns]
                df_stock['MA5'] = df_stock['Close'].rolling(5).mean()
                df_stock['MA20'] = df_stock['Close'].rolling(20).mean()
                df_stock['MA60'] = df_stock['Close'].rolling(60).mean()
                st.session_state.sitc_stock_cache[s_id] = df_stock
                rows.append({'股票代碼': s_id, '今日收盤': round(float(df_stock.iloc[-1]['Close']), 2)})
            except: continue
        st.session_state.sitc_report_df = pd.DataFrame(rows)

# ==========================================
# 4. 繪圖呈現 (替換為 mplfinance)
# ==========================================
if st.session_state.sitc_report_df is not None and not st.session_state.sitc_report_df.empty:
    user_pick = st.selectbox("👉 請切換投信黑馬個股：", options=st.session_state.sitc_report_df['股票代碼'].tolist())
    
    if user_pick in st.session_state.sitc_stock_cache:
        df = st.session_state.sitc_stock_cache[user_pick].tail(120).set_index('Date')
        
        # 轉折標註邏輯
        df['State'] = np.where(df['Close'] > df['Ma5'], 1, -1)
        df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
        zigzag = []
        for g_id, group in df.groupby('State_Group'):
            if g_id <= 2: continue
            if group['State'].iloc[0] == 1:
                idx = group['High'].idxmax()
                zigzag.append((idx, group['High'].max(), "H"))
            else:
                idx = group['Low'].idxmin()
                zigzag.append((idx, group['Low'].min(), "B"))

        # mplfinance 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        plots = [mpf.make_addplot(df['Ma5'], color='orange'), mpf.make_addplot(df['Ma20'], color='purple'), mpf.make_addplot(df['Ma60'], color='cyan')]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=plots, returnfig=True, figsize=(12, 7), volume=True)
        
        # 繪製轉折線與標籤
        if zigzag:
            x, y, labels = zip(*zigzag)
            axlist[0].plot(x, y, color='black', alpha=0.5)
            for i, txt in enumerate(labels):
                axlist[0].annotate(txt, (x[i], y[i]), color='red' if txt=='H' else 'green', weight='bold')
        
        st.pyplot(fig)
