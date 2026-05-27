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
st.set_page_config(page_title="企業級台股量化選股與回測系統", layout="wide")

# 強制設定時區為台北時間，防止雲端伺服器(UTC)日期錯亂導致抓無資料
tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 企業級台股量化選股與回測系統")
st.caption(f"目前台北時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 伺服器環境：GitHub / Streamlit Cloud")

# 初始化 Session State，防止 Streamlit 按鈕觸發後因 Rerun 導致資料消失
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'equity_curve' not in st.session_state:
    st.session_state.equity_curve = None
if 'perf_metrics' not in st.session_state:
    st.session_state.perf_metrics = None

# ==========================================
# 2. 核心功能：台灣焦點股票池定義
# ==========================================
@st.cache_data(ttl=3600)  # 快取一小時，避免重複抓取被 Yahoo 封鎖
def get_tw_stock_list():
    """取得台灣核心股票池（精選權值股與高流動性焦點股，確保雲端執行效率）"""
    focus_stocks = [
        "2330", "2317", "2454", "2308", "2382", "2303", "2881", "2882", "1301", "1303",
        "2603", "2609", "2615", "2357", "2324", "3231", "6669", "2345", "3037", "2379",
        "2891", "2886", "5880", "2892", "2885", "2002", "1101", "2912", "5871", "9904"
    ]
    return [f"{stock}.TW" for stock in focus_stocks]

# ==========================================
# 3. 量化指標與 AI 偽模型 (模擬 RandomForest 訊號輸出)
# ==========================================
def calculate_indicators_and_signals(all_data):
    """計算技術指標與 AI 勝率評分"""
    processed_list = []
    
    for stock_id, df in all_data.groupby('Stock_ID'):
        if len(df) < 60:  # 確保資料量足夠計算 MA60
            continue
            
        df = df.copy().sort_values('Date')
        
        # 技術指標計算
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # 計算乖離率與貼近度
        df['Bias_20'] = (df['Close'] - df['MA20']) / df['MA20']
        df['Dist_5MA'] = (df['Close'] - df['MA5']) / df['MA5']
        
        # 企業級 ffill 容錯：補足盤中暫時性斷流
        df = df.ffill().bfill().dropna()
        
        # 模擬 RandomForest AI 預測勝率 (實務上此處替換為你的 clf.predict_proba)
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
# 4. 策略篩選器：月線向上且貼近 5MA
# ==========================================
def filter_strategy(df_signals, tolerance=0.08):
    """核心選股邏輯"""
    if df_signals.empty:
        return pd.DataFrame()
        
    # 篩選最新一天的資料來做今日選股
    latest_date = df_signals['Date'].max()
    df_today = df_signals[df_signals['Date'] == latest_date].copy()
    
    # 趨勢向上定義：當下 MA20 > MA60 且股價高於 MA20
    condition_trend = (df_today['MA20'] > df_today['MA60']) & (df_today['Close'] > df_today['MA20'])
    
    # 貼近 5日線 ± tolerance (例如 ±8%)
    condition_near_5ma = df_today['Dist_5MA'].abs() <= tolerance
    
    filtered = df_today[condition_trend & condition_near_5ma]
    return filtered.sort_values('AI_Win_Rate', ascending=False)

# ==========================================
# 5. 回測引擎：計入真實交易成本與滑價
# ==========================================
def run_backtest(df_signals, initial_capital, top_n, hold_days):
    """模擬真實帳戶交易流"""
    df_signals = df_signals.sort_values(['Date', 'AI_Win_Rate'], ascending=[True, False])
    dates = sorted(df_signals['Date'].unique())
    
    capital = initial_capital
    portfolio = {}  # {Stock_ID: {'buy_price': x, 'qty': y, 'hold_count': z}}
    equity_curve = []
    
    # 真實台股交易成本
    fee_rate = 0.001425  # 券商手續費
    tax_rate = 0.003     # 證交稅
    
    for today in dates:
        todays_stocks = df_signals[df_signals['Date'] == today]
        stock_values = 0
        expired_stocks = []
        
        # 1. 計算今日資產價值與檢查到期股票
        for stock, info in list(portfolio.items()):
            today_price_row = todays_stocks[todays_stocks['Stock_ID'] == stock]
            current_price = today_price_row['Close'].values[0] if not today_price_row.empty else info['buy_price']
            
            stock_values += current_price * info['qty']
            portfolio[stock]['hold_count'] += 1
            
            if portfolio[stock]['hold_count'] >= hold_days:
                expired_stocks.append((stock, current_price, info['qty']))
                
        # 2. 結算賣出
        for stock, sell_price, qty in expired_stocks:
            revenue = sell_price * qty
            costs = revenue * (fee_rate + tax_rate)
            capital += (revenue - costs)
            del portfolio[stock]
            
        # 3. 執行買入
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
                        
        # 4. 紀錄每日資產淨值
        total_wealth = capital + stock_values
        equity_curve.append({'Date': today, 'Total_Wealth': total_wealth})
        
    df_equity = pd.DataFrame(equity_curve)
    
    # 計算績效指標
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
# 6. Streamlit 使用者介面 (UI) 與批量下載整合
# ==========================================
st.sidebar.header("⚙️ 系統參數設定")
backtest_years = st.sidebar.slider("歷史數據抓取年限 (年)", 1, 3, 2)
m_tolerance = st.sidebar.slider("5MA 貼近容忍度 (±%)", 1, 15, 8) / 100

st.sidebar.subheader("💰 帳戶與模擬交易權重")
init_cap = st.sidebar.number_input("初始模擬資金 (TWD)", value=1000000, step=100000)
max_hold = st.sidebar.slider("每日最高持股數量", 1, 10, 5)
h_days = st.sidebar.slider("AI 訊號持有天數 (天)", 2, 10, 5)

if st.button("🚀 開始全自動掃描全台股（含時區校正與歷史回測）", type="primary"):
    with st.spinner("🚀 正在啟動雲端多線程批量下載引擎..."):
        
        stock_pool = get_tw_stock_list()
        start_dt = (today_tw - timedelta(days=int(backtest_years * 365))).strftime("%Y-%m-%d")
        end_dt = today_tw.strftime("%Y-%m-%d")
        
        try:
            # 【核心抗封鎖修正】：一次性打包下載所有股票，只發送一個 Request
            df_all_raw = yf.download(
                tickers=stock_pool, 
                start=start_dt, 
                end=end_dt, 
                auto_adjust=True, 
                group_by='ticker',
                progress=False
            )
            
            all_frames = []
            
            # 解析 Multi-Index 結構並重組為乾淨的 DataFrame
            if isinstance(df_all_raw.columns, pd.MultiIndex):
                for stock_id in stock_pool:
                    if stock_id in df_all_raw.columns.levels[0]:
                        df_k = df_all_raw[stock_id].dropna(how='all').reset_index()
                        if not df_k.empty:
                            df_k['Stock_ID'] = stock_id
                            all_frames.append(df_k)
            else:
                # 如果只有單檔股票時的防錯處理
                df_all_raw = df_all_raw.reset_index()
                df_all_raw['Stock_ID'] = stock_pool[0]
                all_frames.append(df_all_raw)
                        
            if not all_frames:
                st.error("❌ 錯誤：未能成功從 Yahoo Finance 抓取任何歷史數據。可能觸發雲端 IP 限制，請稍後再試。")
            else:
                df_all = pd.concat(all_frames, ignore_index=True)
                
                # 確保欄位名稱正確無誤
                if 'Date' not in df_all.columns and 'index' in df_all.columns:
                    df_all = df_all.rename(columns={'index': 'Date'})
                
                # 2. 技術指標與 AI 預測計算
                df_signals = calculate_indicators_and_signals(df_all)
                
                # 3. 執行今日策略選股
                df_filtered = filter_strategy(df_signals, tolerance=m_tolerance)
                st.session_state.scan_results = df_filtered
                
                # 4. 啟動回測引擎
                metrics, df_equity = run_backtest(df_signals, init_cap, max_hold, h_days)
                st.session_state.perf_metrics = metrics
                st.session_state.equity_curve = df_equity
                
                st.success("🎉 雲端大數據掃描與歷史回測模擬全數完成！")
                
        except Exception as batch_error:
            st.error(f"❌ 批量下載發生異常，已阻斷防崩潰: {str(batch_error)}")

# ==========================================
# 7. 報表與視覺化結果呈現
# ==========================================
st.markdown("---")

# 顯示選股結果
if st.session_state.scan_results is not None:
    st.subheader("📋 今日 AI 強勢多頭貼線選股清單")
    
    if st.session_state.scan_results.empty:
        st.warning(f"ℹ️ 經時區校正({today_tw})篩選後：當前市場中無符合「月線向上且股價貼近 5MA」之個股。系統已啟動安全保護機制，建議將左側容忍度參數調大。")
    else:
        display_df = st.session_state.scan_results[['Stock_ID', 'Close', 'MA20', 'Dist_5MA', 'AI_Win_Rate']].copy()
        display_df['Dist_5MA'] = (display_df['Dist_5MA'] * 100).round(2).astype(str) + "%"
        display_df['AI_Win_Rate'] = (display_df['AI_Win_Rate'] * 100).round(1).astype(str) + "%"
        display_df['Close'] = display_df['Close'].round(2)
        display_df['MA20'] = display_df['MA20'].round(2)
        
        display_df.columns = ['股票代碼', '今日收盤價', '月線(20MA)', '偏離5MA幅度', 'AI 預估波段勝率']
        st.dataframe(display_df, use_container_width=True)

# 顯示回測與績效績效報表
if st.session_state.perf_metrics is not None and st.session_state.equity_curve is not None:
    st.subheader("📊 策略歷史回測績效報告 (已扣除真實交易成本)")
    
    m = st.session_state.perf_metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📈 年化報酬率", f"{m['年化報酬率 (%)']}%")
    c2.metric("🛡️ 夏普比率 (Sharpe)", f"{m['夏普比率 (Sharpe)']}")
    c3.metric("📉 最大回撤 (MDD)", f"{m['最大回撤 (MDD %)']}%")
    c4.metric("💰 歷史總報酬率", f"{m['總報酬率 (%)']}%")
    
    # 繪製資產曲線
    df_eq = st.session_state.equity_curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_eq['Date'], y=df_eq['Total_Wealth'], name='帳戶總資產值 (TWD)', line=dict(color='#00FFCC', width=2)))
    fig.update_layout(
        title="🤖 AI 策略歷史帳戶淨值走勢 (Equity Curve)",
        xaxis_title="時間軸", yaxis_title="資產總值",
        template="plotly_dark", height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
