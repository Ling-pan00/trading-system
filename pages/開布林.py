import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="布林通道突破量化選股 Pro", layout="wide")
st.title("📊 布林通道突破量化交易系統（上軌強勢突破 + 500張量能過濾）")

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

stock_list = get_stock_list()
ticker_map = {s["ticker"]: s for s in stock_list}
tickers = list(ticker_map.keys())

st.write(f"📦 **目前監測台股總數：{len(tickers)} 檔**（已自動過濾權證、存託憑證等）")

# ==========================================
# 📈 技術指標與布林通道計算
# ==========================================
def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    
    # 計算布林通道 (Bollinger Bands, 用於選股與風控)
    std20 = df["Close"].rolling(20).std()
    df["b_upper"] = df["ma20"] + (std20 * 2)
    df["b_middle"] = df["ma20"]
    df["b_lower"] = df["ma20"] - (std20 * 2)
    
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

# ==========================================
# 🎯 布林通道突破策略條件檢查
# ==========================================
def check_bollinger_breakout(df):
    """
    布林通道突破策略檢測邏輯：
    1. 當前收盤價向上突破或貼近布林上軌（Close >= b_upper * 0.98）。
    2. 收盤價必須大於 20 日均線（確認短中期多頭趨勢）。
    """
    try:
        if df is None or df.empty or len(df) < 20:
            return False, 0, 0

        current_price = df["Close"].iloc[-1]
        upper_band = df["b_upper"].iloc[-1]
        lower_band = df["b_lower"].iloc[-1]
        ma20 = df["ma20"].iloc[-1]

        is_above_ma20 = current_price > ma20
        is_breakout = current_price >= (upper_band * 0.98)

        if is_above_ma20 and is_breakout:
            return True, upper_band, lower_band

        return False, 0, 0
    except:
        return False, 0, 0

# ==========================================
# 💰 進出場策略與風控水位
# ==========================================
def trade_levels(price, upper_band, lower_band):
    entry = round(price, 2)
    stop = round(lower_band, 2)  
    target = round(price + (price - lower_band), 2)  
    return entry, stop, target

# ==========================================
# 🎨 轉折 K 線圖與高低點標註繪製模組 (5MA / 10MA / 20MA)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=150)).strftime('%Y-%m-%d')
    
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()

    df_chart['Close'] = pd.to_numeric(df_chart['Close'], errors='coerce')
    df_chart['High'] = pd.to_numeric(df_chart['High'], errors='coerce')
    df_chart['Low'] = pd.to_numeric(df_chart['Low'], errors='coerce')

    df_chart = df_chart.dropna(subset=['Close', '5MA', '10MA', '20MA']).copy()

    # 計算轉折點 (Zigzag H/B)
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

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 5MA/10MA/20MA 轉折波段圖")
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
            <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

    plots = [
        mpf.make_addplot(df_chart['5MA'], color='orange', width=1),
        mpf.make_addplot(df_chart['10MA'], color='blue', width=1),
        mpf.make_addplot(df_chart['20MA'], color='purple', width=1.2)
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
if st.button("🚀 執行布林突破策略選股"):
    results = []
    batch_size = 150  
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    status_text = st.empty()

    for i in range(total_batches):
        status_text.text(f"正在掃描市場布林通道突破... 進度：{i+1}/{total_batches} 批次")
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

                if df.empty or len(df) < 20:
                    continue

                df = add_indicators(df)
                price = df["Close"].iloc[-1]
                volume = df["Volume"].iloc[-1]
                
                volume_sheets = volume / 1000 
                if volume_sheets < 500:
                    continue

                is_breakout, upper_band, lower_band = check_bollinger_breakout(df)
                if not is_breakout:
                    continue

                entry, stop, target = trade_levels(price, upper_band, lower_band)

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "當日收盤": round(price, 2),
                    "布林上軌": round(upper_band, 2),
                    "成交量(張)": int(volume_sheets),
                    "建議進場": entry,
                    "防守停損": stop,
                    "波段目標": target
                })
            except:
                continue
        progress.progress((i + 1) / total_batches)
    
    status_text.text("🎉 布林突破策略選股完成！")

    if not results:
        st.warning("⚠️ 經過成交量（500張）與布林通道突破條件限制篩選後，目前沒有符合標準的標的。")
        st.session_state["qualified_stocks"] = pd.DataFrame()
    else:
        df_res = pd.DataFrame(results).sort_values(by="成交量(張)", ascending=False).reset_index(drop=True)
        st.session_state["qualified_stocks"] = df_res
        st.session_state["stock_idx"] = 0

# ==========================================
# 📊 畫面渲染與互動選單機制
# ==========================================
if "qualified_stocks" in st.session_state:
    saved_df = st.session_state["qualified_stocks"]
    st.subheader(f"📊 布林通道突破策略精選總名單（共 {len(saved_df)} 檔）")
    
    if not saved_df.empty:
        display_df = saved_df.drop(columns=["ticker"])
        st.dataframe(display_df, use_container_width=True)
        
        stock_options = [f"{row['代號']} {row['名稱']}" for _, row in saved_df.iterrows()]
        
        if "stock_idx" not in st.session_state:
            st.session_state["stock_idx"] = 0
            
        if st.session_state["stock_idx"] >= len(stock_options):
            st.session_state["stock_idx"] = 0

        st.write(f"🔍 **切換檢視 K 線圖：**")
        btn_col1, sel_col, btn_col2 = st.columns([1, 4, 1])
        
        with btn_col1:
            if st.button("⏮️ 上一檔", use_container_width=True):
                if st.session_state["stock_idx"] > 0:
                    st.session_state["stock_idx"] -= 1
                else:
                    st.session_state["stock_idx"] = len(stock_options) - 1
                st.rerun()

        with sel_col:
            def on_select_change():
                selected_val = st.session_state["single_stock_selector"]
                st.session_state["stock_idx"] = stock_options.index(selected_val)

            st.selectbox(
                "選擇股票：", 
                stock_options, 
                index=st.session_state["stock_idx"],
                key="single_stock_selector",
                on_change=on_select_change,
                label_visibility="collapsed"
            )

        with btn_col2:
            if st.button("⏭️ 下一檔", use_container_width=True):
                if st.session_state["stock_idx"] < len(stock_options) - 1:
                    st.session_state["stock_idx"] += 1
                else:
                    st.session_state["stock_idx"] = 0
                st.rerun()
        
        final_idx = st.session_state["stock_idx"]
        target_row = saved_df.iloc[final_idx]
        
        draw_zigzag_chart(target_row["ticker"], target_row["名稱"])
    else:
        st.info("目前無符合條件股票")
