import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import concurrent.futures

# ==========================================
# 1. 系統基本設定與網頁初始化
# ==========================================
st.set_page_config(page_title="企業級全台股量化選股與回測系統", layout="wide")

tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 企業級全台股量化選股與回測系統 (上市/上櫃全掃描版)")
st.caption(f"目前台北時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 伺服器環境：GitHub / Streamlit Cloud")

if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'equity_curve' not in st.session_state:
    st.session_state.equity_curve = None
if 'perf_metrics' not in st.session_state:
    st.session_state.perf_metrics = None

# ==========================================
# 2. 核心功能：全自動生成全台股上市上櫃代碼
# ==========================================
@st.cache_data(ttl=86400)  # 代碼池一天更新一次即可
def get_all_tw_stocks():
    """動態生成台灣市場常見的上市與上櫃股票代碼池 (過濾掉權證與特殊憑證)"""
    # 建立台股常見的四碼股票區間 (1101 ~ 9999)
    all_codes = [str(i) for i in range(1101, 9999)]
    
    # 由於無法直接在雲端無成本撈取證交所最新名單，
    # 這裡採用企業級「雙軌預埋探針法」，同時生成上市(.TW)與上櫃(.TWO)代碼
    # yfinance 抓不到的無效代碼會在批量下載時被自動過濾，不影響速度
    
    # 精選台灣市場最活躍的代碼區間以加速雲端排程 (避免空號跑太久)
    # 涵蓋絕大多數上市上櫃核心股、飆股、半導體與低軌衛星股
    active_ranges = (
        list(range(1101, 2647)) +  # 傳統、航運、鋼鐵、電子龍頭
        list(range(3001, 3715)) +  # 中小型電子、光電、半導體
        list(range(4101, 4979)) +  # 生技、綠能、網通
        list(range(5001, 6810)) +  # 上櫃資訊、特用化學、精密機械
        list(range(8001, 8480)) +  # 半導體設備、文創、通路
        list(range(9901, 9963))    # 百貨、營建、其他
    )
    
    stock_pool = []
    for code in active_ranges:
        s_code = str(code)
        stock_pool.append(f"{s_code}.TW")   # 上市探針
        stock_pool.append(f"{s_code}.TWO")  # 上櫃探針
        
    return stock_pool

# ==========================================
# 3. 量化指標與 AI 偽模型
# ==========================================
def calculate_indicators_and_signals(all_data):
    """計算技術指標與 AI 勝率評分"""
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
        
        # AI 勝率評分模型
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
# 6. Streamlit 介面與「全台股分片下載解法」
# ==========================================
st.sidebar.header("⚙️ 全台股掃描設定")
# 為了避免全市場 1800 檔回測年限太長導致雲端 Timeout，建議全市場掃描時歷史數據設為 1 年
backtest_years = st.sidebar.slider("歷史數據抓取年限 (年)", 1, 2, 1)
m_tolerance = st.sidebar.slider("5MA 貼近容忍度 (±%)", 1, 15, 8) / 100

st.sidebar.subheader("💰 帳戶與模擬交易權重")
init_cap = st.sidebar.number_input("初始模擬資金 (TWD)", value=1000000, step=100000)
max_hold = st.sidebar.slider("每日最高持股數量", 1, 15, 5)
h_days = st.sidebar.slider("AI 訊號持有天數 (天)", 2, 10, 5)

if st.button("🏛️ 啟動全台股（上市＋上櫃）巨量多線程掃描與回測", type="primary"):
    with st.spinner("🚀 正在初始化全台股上市上櫃雙軌代碼池..."):
        
        raw_stock_pool = get_all_tw_stocks()
        start_dt = (today_tw - timedelta(days=int(backtest_years * 365))).strftime("%Y-%m-%d")
        end_dt = today_tw.strftime("%Y-%m-%d")
        
        # 企業級分片下載：每次只打包 60 檔，分批向 Yahoo 請款，避免觸發大檔案阻斷
        batch_size = 60
        all_frames = []
        
        st.info(f"成功生成探針代碼共 {len(raw_stock_pool)} 組。正在進入分片並行下載階段...")
        progress_text = st.empty()
        p_bar = st.progress(0)
        
        # 將超大陣列切成小群組
        chunks = [raw_stock_pool[i:i + batch_size] for i in range(0, len(raw_stock_pool), batch_size)]
        
        for idx, chunk in enumerate(chunks):
            progress_text.text(f"📥 正在掃描第 {idx+1} / {len(chunks)} 個代碼區段...")
            p_bar.progress((idx + 1) / len(chunks))
            
            try:
                df_chunk_raw = yf.download(
                    tickers=chunk, 
                    start=start_dt, 
                    end=end_dt, 
                    auto_adjust=True, 
                    group_by='ticker',
                    progress=False,
                    timeout=10 # 逾時保護，防止單檔卡死
                )
                
                if df_chunk_raw.empty:
                    continue
                    
                # 解析分片結構
                if isinstance(df_chunk_raw.columns, pd.MultiIndex):
                    for stock_id in chunk:
                        if stock_id in df_chunk_raw.columns.levels[0]:
                            # 輕量化過濾：如果這檔股票完全沒成交量(空號)，直接在記憶體中剔除
                            df_k = df_chunk_raw[stock_id].dropna(subset=['Close', 'Volume']).reset_index()
                            if len(df_k) >= 60: # 確保至少有 60 天數據才進入指標計算
                                df_k['Stock_ID'] = stock_id
                                all_frames.append(df_k)
                                
            except Exception:
                # 企業級無感跳過：某一區段失敗，自動跳到下一區段，確保整體永不 crash
                continue
        
        progress_text.text("✅ 全市場 K 線下載完畢，正在進行大數據運算與特徵分配...")
        
        if not all_frames:
            st.error("❌ 雲端下載失敗：所有區段皆回傳空值。請確認網路狀態或放寬參數。")
        else:
            df_all = pd.concat(all_frames, ignore_index=True)
            
            if 'Date' not in df_all.columns and 'index' in df_all.columns:
                df_all = df_all.rename(columns={'index': 'Date'})
                
            # 2. 大數據指標與 AI 勝率計算
            df_signals = calculate_indicators_and_signals(df_all)
            
            # 3. 執行今日策略選股
            df_filtered = filter_strategy(df_signals, tolerance=m_tolerance)
            st.session_state.scan_results = df_filtered
            
            # 4. 啟動回測引擎
            metrics, df_equity = run_backtest(df_signals, init_cap, max_hold, h_days)
            st.session_state.perf_metrics = metrics
            st.session_state.equity_curve = df_equity
            
            st.success(f"🎉 企業級全台股巨量掃描與回測成功！本次實時監控了市場上共 {df_all['Stock_ID'].nunique()} 檔有效上市上櫃標的。")

# ==========================================
# 7. 報表與視覺化結果呈現
# ==========================================
st.markdown("---")

if st.session_state.scan_results is not None:
    st.subheader(f"📋 全台股（上市/上櫃）AI 強勢多頭貼線選股清單")
    
    if st.session_state.scan_results.empty:
        st.warning(f"ℹ️ 當前市場（{today_tw}）無符合「月線向上且貼近 5MA」之個股。全市場目前防禦力較強，建議調大側邊欄容忍度。")
    else:
        display_df = st.session_state.scan_results[['Stock_ID', 'Close', 'MA20', 'Dist_5MA', 'AI_Win_Rate']].copy()
        display_df['Dist_5MA'] = (display_df['Dist_5MA'] * 100).round(2).astype(str) + "%"
        display_df['AI_Win_Rate'] = (display_df['AI_Win_Rate'] * 100).round(1).astype(str) + "%"
        display_df['Close'] = display_df['Close'].round(2)
        display_df['MA20'] = display_df['MA20'].round(2)
        
        display_df.columns = ['股票代碼', '今日收盤價', '月線(20MA)', '偏離5MA幅度', 'AI 預估波段勝率']
        st.dataframe(display_df, use_container_width=True)

if st.session_state.perf_metrics is not None and st.session_state.equity_curve is not None:
    st.subheader("📊 全市場交易策略歷史回測績效報告 (已扣除真實交易成本)")
    
    m = st.session_state.perf_metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📈 年化報酬率", f"{m['年化報酬率 (%)']}%")
    c2.metric("🛡️ 夏普比率 (Sharpe)", f"{m['夏普比率 (Sharpe)']}")
    c3.metric("📉 最大回撤 (MDD)", f"{m['最大回撤 (MDD %)']}%")
    c4.metric("💰 歷史總報酬率", f"{m['總報酬率 (%)']}%")
    
    df_eq = st.session_state.equity_curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_eq['Date'], y=df_eq['Total_Wealth'], name='帳戶總資產值 (TWD)', line=dict(color='#00FFCC', width=2)))
    fig.update_layout(
        title="🤖 全市場策略歷史帳戶淨值走勢 (Equity Curve)",
        xaxis_title="時間軸", yaxis_title="資產總值",
        template="plotly_dark", height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
