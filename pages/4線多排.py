import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="四線多排量化選股 Pro", layout="wide")
st.title("📊 四線多頭排列量化交易系統（單一精選清單 + 800張 + 8%防追高）")

# ==========================================
# 📦 股票池模組 (自動抓取台股上市/上櫃代號)
# ==========================================
@st.cache_data(ttl=86400)
def get_stock_list():
    """從 twstock 自動獲取台灣上市與上櫃的 4 位數股票代號"""
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

# 初始化股票資料對照表
stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

st.write(f"📦 **目前監測台股總數：{len(tickers)} 檔**（已自動過濾權證、存託憑證等）")

# ==========================================
# 📈 技術指標計算 (納入 60MA 季線)
# ==========================================
def add_indicators(df):
    """計算策略所需的技術指標，包含 60MA 季線"""
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

# ==========================================
# 💯 因子多頭評分模型
# ==========================================
def score(price, ma5, ma10, ma20, ma60, vol, vol_ma5, change_pct):
    """根據四線多頭排列、量能與當日漲跌進行綜合評分"""
    s = 0
    s += 2 if price > ma5 else 0
    s += 1 if ma5 > ma10 else 0
    s += 1 if ma10 > ma20 else 0
    s += 1 if ma20 > ma60 else 0
    s += 2 if vol > vol_ma5 else 0
    s += 1 if change_pct > 0 else 0
    return s

# ==========================================
# 🎯 策略條件檢查（四線多排 + 基礎過濾）
# ==========================================
def check_strategy(df, price, ma5, ma10, ma20, ma60, s):
    """檢查是否符合嚴格四線多頭排列與多頭趨勢"""
    try:
        if df is None or df.empty or len(df) < 70:
            return False

        # 核心條件：四線多頭排列 (5MA > 10MA > 20MA > 60MA)
        four_line_align = (ma5 > ma10) and (ma10 > ma20) and (ma20 > ma60)
        if not four_line_align:
            return False

        ma20_series = df["ma20"]
        above_ma20 = price > ma20
        ma20_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]  # MA20 趨勢上揚

        # 綜合評分門檻達標（至少 5 分以上）
        if ma20_up and above_ma20 and s >= 5:
            return True

        return False
    except:
        return False

# ==========================================
# 💰 進出場策略與風控水位
# ==========================================
def trade_levels(price, ma5, ma10):
    """給予防守停損與波段目標價配置"""
    stop = ma10             # 以 MA10 為波段防守
    target = price * 1.15   # 目標期待 +15%
    return round(price, 2), round(stop, 2), round(target, 2)


# ==========================================
# 🎨 轉折 K 線圖繪製模組 (含 60MA)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    """繪製 4 個月區間的 5MA 轉折波段圖，並顯示 5/10/20/60 MA"""
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=120)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart['60MA'] = df_chart['Close'].rolling(window=60).mean()

    df_chart['Close'] = pd.to_numeric(df_chart['Close'], errors='coerce')
    df_chart['High'] = pd.to_numeric(df_chart['High'], errors='coerce')
    df_chart['Low'] = pd.to_numeric(df_chart['Low'], errors='coerce')

    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA', '60MA']).copy()

    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()

    zigzag_points = []
    grouped = df_chart.groupby('State_Group')
    group_ids = sorted(df_chart['State_Group'].unique())

    for g_id in group_ids:
        group_data = grouped.get_group(g_id)
        state = group_data['State'].iloc[0]
        if g_id <= 2: continue
        if state == 1:
            highest_idx = group_data['High'].idxmax()
            zigzag_points.append((df_chart.index.get_loc(highest_idx), df_chart.loc[highest_idx, 'High']))
            df_chart.loc[highest_idx, 'Label'] = "H"
        else:
            lowest_idx = group_data['Low'].idxmin()
            zigzag_points.append((df_chart.index.get_loc(lowest_idx), df_chart.loc[lowest_idx, 'Low']))
            df_chart.loc[lowest_idx, 'Label'] = "B"

    def get_ma_details(col_name):
        now = df_chart[col_name].iloc[-1]
        pre = df_chart[col_name].iloc[-2]
        arrow = "▲" if now >= pre else "▼"
        return f"{now:.2f} {arrow}"

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 四線多排 5MA 轉折波段圖")
    st.markdown(f"""
        <div style="
            background-color: #f8f9fa; 
            padding: 10px 15px; 
            border-radius: 5px; 
            margin-top: 5px; 
            margin-bottom: 10px; 
            font-family: monospace; 
            font-size: 14px; 
            font-weight: bold;
            border-left: 5px solid #6c757d;
        ">
            <span style="color: #FF9800; margin-right: 15px;">5MA: {get_ma_details('5MA')}</span>
            <span style="color: #2196F3; margin-right: 15px;">10MA: {get_ma_details('10MA')}</span>
            <span style="color: #9C27B0; margin-right: 15px;">20MA: {get_ma_details('20MA')}</span>
            <span style="color: #009688;">60MA: {get_ma_details('60MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

    plots = [
        mpf.make_addplot(df_chart['5MA'], color='orange', width=1),
        mpf.make_addplot(df_chart['10MA'], color='blue', width=1),
        mpf.make_addplot(df_chart['20MA'], color='purple', width=1),
        mpf.make_addplot(df_chart['60MA'], color='teal', width=1.2)
    ]

    fig, axlist = mpf.plot(
        df_chart, type='candle', style=s_style, addplot=plots, 
        returnfig=True, figsize=(12, 6), volume=True,
        panel_ratios=(4,1)
    )
    
    main_ax = axlist[0]

    if len(zigzag_points) > 1:
        x_coords, y_coords = zip(*zigzag_points)
        main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

    for idx, row in df_chart[df_chart['Label'].notnull()].iterrows():
        x = df_chart.index.get_loc(idx)
        is_h = row['Label'] == "H"
        main_ax.text(x, row['High' if is_h else 'Low'], row['Label'],
                    color='red' if is_h else 'green', weight='bold',
                    ha='center', va='bottom' if is_h else 'top',
                    bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))

    st.pyplot(fig)
    plt.close(fig)


# ==========================================
# 🚀 盤後選股功能
# ==========================================
if st.button("🚀 執行四線多排策略選股"):
    results = []
    batch_size = 150  
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    status_text = st.empty()

    for i in range(total_batches):
        status_text.text(f"正在掃描市場股票... 進度：{i+1}/{total_batches} 批次")
        batch = tickers[i * batch_size:(i + 1) * batch_size]
        
        try:
            data = yf.download(tickers=batch, period="6mo", interval="1d", group_by="ticker", progress=False, threads=True)
        except Exception as e:
            continue

        for t in batch:
            try:
                if len(batch) > 1:
                    if t in data.columns.levels[0]:
                        df = data[t].dropna(subset=["Close"])
                    else:
                        continue
                else:
                    df = data.dropna(subset=["Close"])

                if df.empty or len(df) < 70:
                    continue

                df = add_indicators(df)
                price = df["Close"].iloc[-1]
                volume = df["Volume"].iloc[-1]
                
                # 成交量大於 800 張
                volume_sheets = volume / 1000 
                if volume_sheets < 800:
                    continue

                ma5 = df["ma5"].iloc[-1]
                ma10 = df["ma10"].iloc[-1]
                ma20 = df["ma20"].iloc[-1]
                ma60 = df["ma60"].iloc[-1]
                change_pct = (price - df["Close"].iloc[-2]) / df["Close"].iloc[-2]

                s = score(price, ma5, ma10, ma20, ma60, volume, df["vol_ma5"].iloc[-1], change_pct)
                
                # 檢查四線多排條件
                if not check_strategy(df, price, ma5, ma10, ma20, ma60, s):
                    continue

                entry, stop, target = trade_levels(price, ma5, ma10)

                # 防追高乖離濾網（8% 限制）
                risk_pct = (price - stop) / stop
                if risk_pct > 0.08:
                    continue

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "評分": s,
                    "當日收盤": round(price, 2),
                    "成交量(張)": int(volume_sheets),
                    "建議進場": entry,
                    "防守停損": stop,
                    "波段目標": target
                })
            except:
                continue
        progress.progress((i + 1) / total_batches)
    
    status_text.text("🎉 策略精選選股完成！")

    if not results:
        st.warning("⚠️ 經過成交量（800張）、四線多排與防追高限制（8%）篩選後，目前沒有符合標準的標的。")
        st.session_state["qualified_stocks"] = pd.DataFrame()
    else:
        df_res = pd.DataFrame(results).sort_values(by="成交量(張)", ascending=False).reset_index(drop=True)
        st.session_state["qualified_stocks"] = df_res
        st.session_state["stock_idx"] = 0


# ==========================================
# 📊 畫面渲染與單一名單互動介面
# ==========================================
if "qualified_stocks" in st.session_state:
    saved_df = st.session_state["qualified_stocks"]
    st.subheader(f"📊 四線多排策略精選總名單（共 {len(saved_df)} 檔）")
    
    if not saved_df.empty:
        display_df = saved_df.drop(columns=["ticker"])
        st.dataframe(display_df, use_container_width=True)
        
        stock_options = [f"{row['代號']} {row['名稱']}" for _, row in saved_df.iterrows()]
        
        if "stock_idx" not in st.session_state:
            st.session_state["stock_idx"] = 0
            
        current_idx = st.session_state["stock_idx"]

        st.write(f"🔍 **切換檢視 K 線圖：**")
        btn_col1, sel_col, btn_col2 = st.columns([1, 4, 1])
        
        with btn_col1:
            if st.button("⏮️ 上一檔", use_container_width=True):
                if current_idx > 0:
                    st.session_state["stock_idx"] = current_idx - 1
                    st.rerun()

        with sel_col:
            selected_stock = st.selectbox(
                "選擇股票：", 
                stock_options, 
                index=st.session_state["stock_idx"],
                key="single_stock_selector",
                label_visibility="collapsed"
            )
            new_idx = stock_options.index(selected_stock)
            if new_idx != current_idx:
                st.session_state["stock_idx"] = new_idx
                st.rerun()

        with btn_col2:
            if st.button("⏭️ 下一檔", use_container_width=True):
                if current_idx < len(stock_options) - 1:
                    st.session_state["stock_idx"] = current_idx + 1
                    st.rerun()
        
        final_idx = st.session_state["stock_idx"]
        target_row = saved_df.iloc[final_idx]
        
        draw_zigzag_chart(target_row["ticker"], target_row["名稱"])
    else:
        st.info("目前無符合條件股票")


# ==========================================
# 📈 盤中即時監控模組
# ==========================================
st.markdown("---")
st.subheader("📈 盤中動態監控系統")

def run_monitor_optimized(pool_df):
    if pool_df.empty:
        return pd.DataFrame()
    
    monitor_tickers = pool_df["ticker"].tolist()
    
    try:
        live_data = yf.download(tickers=monitor_tickers, period="10d", interval="1d", group_by="ticker", progress=False, threads=True)
    except:
        st.error("❌ 盤中即時資料獲取失敗，請稍後重試。")
        return pd.DataFrame()

    live_results = []
    
    for _, row in pool_df.iterrows():
        t = row["ticker"]
        try:
            if len(monitor_tickers) > 1:
                df = live_data[t].dropna(subset=["Close"])
            else:
                df = live_data.dropna(subset=["Close"])

            if len(df) < 6:
                continue

            open_now = df["Open"].iloc[-1]
            close_now = df["Close"].iloc[-1]
            ma5 = df["Close"].rolling(5).mean().iloc[-1]
            
            high_5 = df["High"].iloc[-6:-1].max()
            vol_today = df["Volume"].iloc[-1]
            vol_avg = df["Volume"].rolling(5).mean().iloc[-1]

            red_k = close_now > open_now
            above_ma5 = close_now > ma5
            breakout = close_now > high_5
            vol_ok = vol_today > vol_avg

            if red_k and above_ma5 and vol_ok and breakout:
                signal = "🟢 強力BUY (量價齊揚突破)"
            elif red_k and above_ma5:
                signal = "🟡 WATCH (常態轉強)"
            else:
                signal = "🔴 NO (型態轉弱/收黑)"

            live_results.append({
                "代號": row["代號"],
                "名稱": row["名稱"],
                "目前盤中價": round(close_now, 2),
                "即時MA5": round(ma5, 2),
                "紅K": "✅收紅" if red_k else "❌收黑",
                "站上MA5": "✅" if above_ma5 else "❌",
                "量能爆發": "✅爆量" if vol_ok else "❌量縮",
                "突破近5日高": "✅突破" if breakout else "❌未過",
                "📢 盤中即時訊號": signal
            })
        except:
            continue
            
    return pd.DataFrame(live_results)


if st.button("🔄 刷新盤中監控訊號"):
    if "qualified_stocks" not in st.session_state:
        st.warning("⚠️ 請先執行盤後策略選股以建立監控名單。")
        st.stop()

    saved_df = st.session_state["qualified_stocks"]
    if not saved_df.empty:
        res_df = run_monitor_optimized(saved_df)
        if not res_df.empty:
            st.dataframe(res_df, use_container_width=True)
        else:
            st.info("暫無有效即時數據")
    else:
        st.info("ℹ️ 無基礎選股標的，盤中跳過監控。")
