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
st.set_page_config(page_title="企業級核心科技股量化選股與回測系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 企業級科技與機電核心股量化選股系統")
st.caption(f"目前台北時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 伺服器環境：GitHub / Streamlit Cloud")

st.info("🎯 **當前監控產業**：電機機械、電器電纜、化學工業、半導體業、電腦週邊、光電業、通信網路、電子組件、電子通路、資訊服務、其他電子、數位雲端")

# 初始化 Session State
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'equity_curve' not in st.session_state:
    st.session_state.equity_curve = None
if 'perf_metrics' not in st.session_state:
    st.session_state.perf_metrics = None
if 'raw_df_all' not in st.session_state:
    st.session_state.raw_df_all = None  
if 'mobile_selected_stock' not in st.session_state:
    st.session_state.mobile_selected_stock = None  # 用來記錄手機點擊了哪檔股票

# ==========================================
# 2. 核心功能：精準科技與機電代碼池
# ==========================================
@st.cache_data(ttl=86400)
def get_all_tw_stocks():
    tech_and_machinery_ranges = (
        list(range(1503, 1627)) +  
        list(range(1701, 1796)) +  
        list(range(2301, 2498)) +  
        list(range(3001, 3715)) +  # 含信錦 1582
        list(range(4904, 4977)) +  
        list(range(5203, 5498)) +  
        list(range(6104, 6285)) +  
        list(range(6405, 6811)) +  
        list(range(8011, 8478)) +  
        list(range(9914, 9958))    
    )
    stock_pool = []
    for code in tech_and_machinery_ranges:
        s_code = str(code)
        stock_pool.append(f"{s_code}.TW")   
        stock_pool.append(f"{s_code}.TWO")  
    return stock_pool

# ==========================================
# 3. 量化指標與 AI 偽模型
# ==========================================
def calculate_indicators_and_signals(all_data):
    processed_list = []
    for stock_id, df in all_data.groupby('Stock_ID'):
        if len(df) < 60:
            continue
        df = df.copy().sort_values('Date')
        
        # 技術指標計算
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        df['Bias_20'] = (df['Close'] - df['MA20']) / df['MA20']
        df['Dist_5MA'] = (df['Close'] - df['MA5']) / df['MA5']
        
        df = df.ffill().bfill().dropna()
        
        trend_score = np.where(df['MA20'] > df['MA60'], 0.6, 0.4)
        bias_score = np.where(df['Bias_20'].abs() < 0.1, 0.15, 0.05)
        vol_score = np.where(df['Volume'] > df['Volume'].rolling(10).mean(), 0.1, 0.05)
        
        df['AI_Win_Rate'] = trend_score + bias_score + vol_score
        df['AI_Win_Rate'] = df['AI_Win_Rate'].clip(0.01, 0.99)
        processed_list.append(df)
        
    if not processed_list:
        return pd.DataFrame()
    return pd.concat(processed_list, ignore_index=True)

# ==========================================
# 4. 策略篩選器
# ==========================================
def filter_strategy(df_signals, tolerance=0.08):
    if df_signals.empty:
        return pd.DataFrame()
    latest_date = df_signals['Date'].max()
    df_today = df_signals[df_signals['Date'] == latest_date].copy()
    
    condition_trend = (df_today['MA20'] > df_today['MA60']) & (df_today['Close'] > df_today['MA20'])
    condition_near_5ma = df_today['Dist_5MA'].abs() <= tolerance
    
    filtered = df_today[condition_trend & condition_near_5ma]
    return filtered.sort_values('AI_Win_Rate', ascending=False)

# ==========================================
# 5. 回測引擎
# ==========================================
def run_backtest(df_signals, initial_capital, top_n, hold_days):
    df_signals = df_signals.sort_values(['Date', 'AI_Win_Rate'], ascending=[True, False])
    dates = sorted(df_signals['Date'].unique())
    capital = initial_capital
    portfolio = {}
    equity_curve = []
    
    fee_rate = 0.001425
    tax_rate = 0.003
    
    for today in dates:
        todays_stocks = df_signals[df_signals['Date'] == today]
        stock_values = 0
        expired_stocks = []
        
        for stock, info in list(portfolio.items()):
            today_price_row = todays_stocks[todays_stocks['Stock_ID'] == stock]
            current_price = today_price_row['Close'].values[0] if not today_price_row.empty else info['buy_price']
            stock_values += current_price * info['qty']
            portfolio[stock]['hold_count'] += 1
            if portfolio[stock]['hold_count'] >= hold_days:
                expired_stocks.append((stock, current_price, info['qty']))
                
        for stock, sell_price, qty in expired_stocks:
            revenue = sell_price * qty
            costs = revenue * (fee_rate + tax_rate)
            capital += (revenue - costs)
            del portfolio[stock]
            
        available_slots = top_n - len(portfolio)
        if available_slots > 0:
            candidates = todays_stocks[~todays_stocks['Stock_ID'].isin(portfolio.keys())].head(available_slots)
            if not candidates.empty:
                cash_per_stock = capital / available_slots
                for _, row in candidates.iterrows():
                    sid = row['Stock_ID']
                    b_price = row['Close']
                    if b_price <= 0: continue
                    qty = int(cash_per_stock / (b_price * (1 + fee_rate)))
                    if qty > 0:
                        cost = qty * b_price * (1 + fee_rate)
                        capital -= cost
                        portfolio[sid] = {'buy_price': b_price, 'qty': qty, 'hold_count': 0}
                        
        total_wealth = capital + stock_values
        equity_curve.append({'Date': today, 'Total_Wealth': total_wealth})
        
    df_equity = pd.DataFrame(equity_curve)
    df_equity['Daily_Return'] = df_equity['Total_Wealth'].pct_change()
    total_return = (df_equity['Total_Wealth'].iloc[-1] / initial_capital) - 1
    total_days = (df_equity['Date'].max() - df_equity['Date'].min()).days
    ann_return = (1 + total_return) ** (365 / total_days) - 1 if total_days > 0 else 0
    daily_vol = df_equity['Daily_Return'].std()
    ann_vol = daily_vol * np.sqrt(252) if daily_vol > 0 else 0
    sharpe = (ann_return - 0.015) / ann_vol if ann_vol > 0 else 0
    
    df_equity['Peak'] = df_equity['Total_Wealth'].cummax()
    df_equity['Drawdown'] = (df_equity['Total_Wealth'] - df_equity['Peak']) / df_equity['Peak']
    max_mdd = df_equity['Drawdown'].min()
    
    metrics = {
        "總報酬率 (%)": round(total_return * 100, 2),
        "年化報酬率 (%)": round(ann_return * 100, 2),
        "夏普比率 (Sharpe)": round(sharpe, 2),
        "最大回撤 (MDD %)": round(max_mdd * 100, 2)
    }
    return metrics, df_equity

# ==========================================
# 6. Streamlit 介面與事件控制
# ==========================================
st.sidebar.header("⚙️ 核心科技股掃描設定")
backtest_years = st.sidebar.slider("歷史數據抓取年限 (年)", 1, 2, 1)
m_tolerance = st.sidebar.slider("5MA 貼近容忍度 (±%)", 1, 15, 8) / 100

st.sidebar.subheader("💰 帳戶與模擬交易權重")
init_cap = st.sidebar.number_input("初始模擬資金 (TWD)", value=1000000, step=100000)
max_hold = st.sidebar.slider("每日最高持股數量", 1, 15, 5)
h_days = st.sidebar.slider("AI 訊號持有天數 (天)", 2, 10, 5)

if st.button("🏛️ 啟動 12 大科技類別全自動盤後掃描與回測", type="primary"):
    with st.spinner("🚀 正在初始化核心科技股雙軌代碼池..."):
        raw_stock_pool = get_all_tw_stocks()
        start_dt = (today_tw - timedelta(days=int(backtest_years * 365))).strftime("%Y-%m-%d")
        end_dt = today_tw.strftime("%Y-%m-%d")
        
        batch_size = 60
        all_frames = []
        
        st.info(f"篩選出核心科技群組共 {len(raw_stock_pool)} 組。進入分片並行下載階段...")
        progress_text = st.empty()
        p_bar = st.progress(0)
        chunks = [raw_stock_pool[i:i + batch_size] for i in range(0, len(raw_stock_pool), batch_size)]
        
        for idx, chunk in enumerate(chunks):
            progress_text.text(f"📥 正在掃描第 {idx+1} / {len(chunks)} 個科技股代碼區段...")
            p_bar.progress((idx + 1) / len(chunks))
            try:
                df_chunk_raw = yf.download(tickers=chunk, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False, timeout=10)
                if df_chunk_raw.empty: continue
                if isinstance(df_chunk_raw.columns, pd.MultiIndex):
                    for stock_id in chunk:
                        if stock_id in df_chunk_raw.columns.levels[0]:
                            df_k = df_chunk_raw[stock_id].dropna(subset=['Close', 'Volume']).reset_index()
                            if len(df_k) >= 60:
                                df_k['Stock_ID'] = stock_id
                                all_frames.append(df_k)
            except Exception:
                continue
        
        progress_text.text("✅ 核心 K 線下載完畢，正在進行大數據運算與特徵分配...")
        
        if not all_frames:
            st.error("❌ 雲端下載失敗：未成功取得任何核心科技股數據。")
        else:
            df_all = pd.concat(all_frames, ignore_index=True)
            if 'Date' not in df_all.columns and 'index' in df_all.columns:
                df_all = df_all.rename(columns={'index': 'Date'})
                
            df_signals = calculate_indicators_and_signals(df_all)
            st.session_state.raw_df_all = df_signals 
            
            df_filtered = filter_strategy(df_signals, tolerance=m_tolerance)
            st.session_state.scan_results = df_filtered
            
            # 預設手機檢視第一檔
            if not df_filtered.empty:
                st.session_state.mobile_selected_stock = df_filtered.iloc[0]['Stock_ID']
            
            metrics, df_equity = run_backtest(df_signals, init_cap, max_hold, h_days)
            st.session_state.perf_metrics = metrics
            st.session_state.equity_curve = df_equity
            st.success(f"🎉 巨量掃描完成！本次共即時監控了 {df_all['Stock_ID'].nunique()} 檔有效科技個股。")

# ==========================================
# 7. 報表與視覺化結果呈現
# ==========================================
st.markdown("---")

if st.session_state.scan_results is not None:
    st.subheader(f"📋 核心科技股：今日 AI 強勢多頭貼線選股清單")
    
    if st.session_state.scan_results.empty:
        st.warning(f"ℹ️ 當前市場無符合之科技股。")
    else:
        display_df = st.session_state.scan_results[['Stock_ID', 'Close', 'MA20', 'Dist_5MA', 'AI_Win_Rate']].copy()
        display_df['Dist_5MA'] = (display_df['Dist_5MA'] * 100).round(2).astype(str) + "%"
        display_df['AI_Win_Rate'] = (display_df['AI_Win_Rate'] * 100).round(1).astype(str) + "%"
        display_df['Close'] = display_df['Close'].round(2)
        display_df['MA20'] = display_df['MA20'].round(2)
        display_df.columns = ['股票代碼', '今日收盤價', '月線(20MA)', '偏離5MA幅度', 'AI 預估波段勝率']
        
        st.dataframe(display_df, use_container_width=True)

        # ==========================================
        # 🔥 專為手機優化：手機快打按鈕連動區
        # ==========================================
        st.markdown("---")
        st.subheader("📱 手機專用：點擊下方按鈕看日 K 線圖")
        st.caption("👇 用手指直接點擊下方任一個股票代號，日 K 線圖就會在下方立刻切換！")
        
        candidate_list = st.session_state.scan_results['Stock_ID'].tolist()
        
        # 做出橫向排版的手機按鈕，每 3 個一橫列
        cols = st.columns(3)
        for idx, s_id in enumerate(candidate_list):
            col_target = cols[idx % 3]
            # 如果目前這檔是被選中的，按鈕用彩色亮色區分（在 st 裡面用 type='primary'）
            is_active = (s_id == st.session_state.mobile_selected_stock)
            btn_type = "primary" if is_active else "secondary"
            
            if col_target.button(f"📊 {s_id}", key=f"btn_{s_id}", type=btn_type, use_container_width=True):
                st.session_state.mobile_selected_stock = s_id
                st.rerun() # 立即重刷頁面更新圖表
                
        # 繪製 K 線圖
        current_view_stock = st.session_state.mobile_selected_stock if st.session_state.mobile_selected_stock else candidate_list[0]
            
        if current_view_stock and st.session_state.raw_df_all is not None:
            st.markdown(f"### 📈 正在檢視日 K 線：**{current_view_stock}**")
            
            stock_k_data = st.session_state.raw_df_all[st.session_state.raw_df_all['Stock_ID'] == current_view_stock].sort_values('Date')
            plot_df = stock_k_data.tail(90) # 手機畫面小，看 90 天最清晰
            
            fig_k = go.Figure()
            
            # 蠟燭 K 線
            fig_k.add_trace(go.Candlestick(
                x=plot_df['Date'],
                open=plot_df['Open'], high=plot_df['High'],
                low=plot_df['Low'], close=plot_df['Close'],
                name='日 K 線',
                increasing_line_color='#FF3333',  
                decreasing_line_color='#00AA00'   
            ))
            
            # 均線系統
            fig_k.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['MA5'], name='5MA', line=dict(color='#FFDD00', width=1.5)))
            fig_k.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['MA20'], name='20MA', line=dict(color='#FF00FF', width=2)))
            fig_k.add_trace(go.Scatter(x=plot_df['Date'], y=plot_df['MA60'], name='60MA', line=dict(color='#00FFFF', width=1.5)))
            
            fig_k.update_layout(
                template="plotly_dark", 
                height=450, # 配合手機高度優化
                xaxis_rangeslider_visible=False,  
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1) # 圖例橫放省空間
            )
            st.plotly_chart(fig_k, use_container_width=True)

# 顯示回測績效報表
if st.session_state.perf_metrics is not None and st.session_state.equity_curve is not None:
    st.markdown("---")
    st.subheader("📊 科技群組交易策略歷史回測績效報告")
    
    m = st.session_state.perf_metrics
    c1, c2 = st.columns(2) # 手機版切成兩欄比較好讀
    c1.metric("📈 年化報酬率", f"{m['年化報酬率 (%)']}%")
    c2.metric("🛡️ 夏普比率 (Sharpe)", f"{m['夏普比率 (Sharpe)']}")
    c1.metric("📉 最大回撤 (MDD)", f"{m['最大回撤 (MDD %)']}%")
    c2.metric("💰 歷史總報酬率", f"{m['總報酬率 (%)']}%")
    
    df_eq = st.session_state.equity_curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_eq['Date'], y=df_eq['Total_Wealth'], name='帳戶總資產值', line=dict(color='#00FFCC', width=2)))
    fig.update_layout(
        title="🤖 歷史帳戶淨值走勢",
        template="plotly_dark", height=350,
        margin=dict(l=10, r=10, t=40, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
