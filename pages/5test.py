import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="四池量化 Pro v2.3", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.3（800張放寬版 + 8%防追高鐵律）")

# ==========================================
# 📦 股票池模組
# ==========================================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
                stocks.append({
                    "code": code,
                    "name": info.name,
                    "ticker": ticker
                })
    return stocks

stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

st.write(f"📦 **目前監測台股總數：{len(tickers)} 檔**")

# ==========================================
# 📈 技術指標計算
# ==========================================
def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

def score(price, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    s += 2 if price > ma5 else 0
    s += 1 if ma5 > ma10 else 0
    s += 1 if ma10 > ma20 else 0
    s += 2 if vol > vol_ma5 else 0
    s += 1 if change_pct > 0 else 0
    return s

# ==========================================
# 🎯 四池分類邏輯
# ==========================================
def classify_pool(s, df, price, ma5, ma10, ma20, open_price):
    try:
        if df is None or df.empty or len(df) < 30:
            return None
        ma20_series = df["ma20"]
        above_ma20 = price > ma20
        ma20_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]
        trend_align = (ma5 > ma10 > ma20)
        red_k = price > open_price
        vol_ok = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]
        accel = df["Close"].pct_change().tail(3).mean() > 0

        if ma20_up and above_ma20 and trend_align and accel and vol_ok and s >= 6:
            return "🔴 第四池"
        if ma20_up and above_ma20 and trend_align and s >= 5:
            not_early = (df["Close"].iloc[-10:] > df["ma5"].iloc[-10:]).all()
            if not_early: return "🔵 第三池"
        if ma20_up and above_ma20 and trend_align and s >= 4:
            return "🟠 第二池"
        if len(df) >= 15:
            was_below_ma5 = (df["Close"].iloc[-15:-1] < df["ma5"].iloc[-15:-1]).any()
            reclaim_ma5 = price > ma5
            prev_high_break = price > df["High"].iloc[-2]
            if ma20_up and above_ma20 and was_below_ma5 and reclaim_ma5 and red_k and prev_high_break:
                return "🟡 第一池"
        return None
    except:
        return None

# ==========================================
# 💰 進出場策略與風控水位
# ==========================================
def trade_levels(price, ma5, ma10, pool):
    if pool == "🔴 第四池": stop, target = ma10, price * 1.25
    elif pool == "🔵 第三池": stop, target = ma5, price * 1.20
    elif pool == "🟠 第二池": stop, target = ma5, price * 1.15
    else: stop, target = ma10, price * 1.10
    return round(price, 2), round(stop, 2), round(target, 2)

# ==========================================
# 🎨 轉折 K 線圖繪製模組
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    if df_chart.empty: return
    if isinstance(df_chart.columns, pd.MultiIndex): df_chart.columns = df_chart.columns.get_level_values(0)
    
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna().copy()

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 3個月 5MA 轉折波段圖")
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df_chart['5MA'], color='orange'), mpf.make_addplot(df_chart['10MA'], color='blue'), mpf.make_addplot(df_chart['20MA'], color='purple')]
    fig, ax = mpf.plot(df_chart, type='candle', style=s_style, addplot=plots, returnfig=True, figsize=(12, 6), volume=True)
    st.pyplot(fig)
    plt.close(fig)

# ==========================================
# 🚀 盤後選股功能
# ==========================================
if st.button("🚀 執行盤後策略選股"):
    results = []
    batch_size = 150
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    for i in range(total_batches):
        batch = tickers[i * batch_size:(i + 1) * batch_size]
        data = yf.download(tickers=batch, period="3mo", interval="1d", group_by="ticker", progress=False)
        for t in batch:
            try:
                df = data[t] if len(batch) > 1 else data
                df = df.dropna()
                if len(df) < 30: continue
                df = add_indicators(df)
                price = float(df["Close"].iloc[-1])
                volume_sheets = float(df["Volume"].iloc[-1] / 1000)
                if volume_sheets < 800: continue
                
                ma5, ma10, ma20 = df["ma5"].iloc[-1], df["ma10"].iloc[-1], df["ma20"].iloc[-1]
                s = score(price, ma5, ma10, ma20, df["Volume"].iloc[-1], df["vol_ma5"].iloc[-1], (price-df["Close"].iloc[-2])/df["Close"].iloc[-2])
                pool = classify_pool(s, df, price, ma5, ma10, ma20, df["Open"].iloc[-1])
                if not pool: continue
                
                entry, stop, target = trade_levels(price, ma5, ma10, pool)
                if (price - stop) / stop > 0.08: continue
                
                results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t, "池別": pool, "分數": s, "當日收盤": round(price, 2), "成交量(張)": int(volume_sheets), "建議進場": entry, "防守停損": stop, "波段目標": target})
            except: continue
        progress.progress((i + 1) / total_batches)
    
    df_res = pd.DataFrame(results)
    for pool_name in ["🔴 第四池", "🔵 第三池", "🟠 第二池", "🟡 第一池"]:
        st.session_state[f"pool_{pool_name}"] = df_res[df_res["池別"] == pool_name].reset_index(drop=True)
        st.session_state[f"idx_{pool_name}"] = 0

# ==========================================
# 📊 畫面渲染與盤中監控 (已修正最新報價獲取)
# ==========================================
def run_monitor_optimized(pool_df):
    if pool_df.empty: return pd.DataFrame()
    monitor_tickers = pool_df["ticker"].tolist()
    # 【修正】：確保抓取的是最新交易日數據，並明確轉型為 float
    live_data = yf.download(tickers=monitor_tickers, period="5d", interval="1d", group_by="ticker", progress=False)
    live_results = []
    for _, row in pool_df.iterrows():
        t = row["ticker"]
        try:
            df = live_data[t] if len(monitor_tickers) > 1 else live_data
            df = df.dropna()
            # 獲取盤中最新成交價
            close_now = float(df["Close"].iloc[-1])
            ma5 = float(df["Close"].rolling(5).mean().iloc[-1])
            
            signal = "🟢 強力BUY" if close_now > ma5 else "🔴 NO"
            live_results.append({"代號": row["代號"], "名稱": row["名稱"], "目前盤中價": round(close_now, 2), "📢 訊號": signal})
        except: continue
    return pd.DataFrame(live_results)

st.markdown("---")
if st.button("🔄 刷新盤中監控訊號"):
    col1, col2 = st.columns(2)
    for p_name, col in [("🟡 第一池", col1), ("🔴 第四池", col2)]:
        with col:
            st.subheader(f"{p_name} 監控")
            if f"pool_{p_name}" in st.session_state:
                res = run_monitor_optimized(st.session_state[f"pool_{p_name}"])
                st.dataframe(res)
