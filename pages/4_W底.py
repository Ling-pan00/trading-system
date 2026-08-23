import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="W底反轉量化選股 Pro", layout="wide")
st.title("📊 W底反轉量化交易系統（雙底突破 + 500張量能過濾）")

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
# 📈 技術指標計算
# ==========================================
def add_indicators(df):
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["ma60"] = df["Close"].rolling(60).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

# ==========================================
# 🎯 W底 (雙底) 策略條件檢查
# ==========================================
def check_w_bottom(df):
    """
    W底（雙底）檢測邏輯：
    1. 檢視過去 90 天的雙底走勢（左低點、中間高點/頸線、右低點）。
    2. 兩次低點價格相近（誤差在 5% 以內）。
    3. 中間高點（頸線）必須高於雙底。
    4. 現價突破或正準備突破頸線，且站上 60MA。
    """
    try:
        if df is None or df.empty or len(df) < 90:
            return False, 0, 0

        recent_df = df.iloc[-90:].copy()
        closes = recent_df["Close"].values
        lows = recent_df["Low"].values
        highs = recent_df["High"].values

        # 尋找第一低點
        mid_len = len(lows) // 2
        l1_idx = np.argmin(lows[:mid_len])
        l1_price = lows[l1_idx]

        # 尋找中間高點 (頸線)
        peak_window = highs[l1_idx+5:-15]
        if len(peak_window) < 5:
            return False, 0, 0
        peak_idx = np.argmax(peak_window) + l1_idx + 5
        peak_price = highs[peak_idx]

        # 尋找第二低點
        l2_window = lows[peak_idx+5:-5]
        if len(l2_window) < 5:
            return False, 0, 0
        l2_idx = np.argmin(l2_window) + peak_idx + 5
        l2_price = lows[l2_idx]

        # 條件 1：兩次低點相近（誤差 5% 內），且中間高點明顯高於低點
        is_w_shape = (abs(l1_price - l2_price) / l1_price < 0.05) and (peak_price > l1_price * 1.05)

        current_price = closes[-1]
        
        # 條件 2：現價突破或貼近頸線（容許 3% 內回測或剛突破 8% 內）
        is_breakout = (current_price >= peak_price * 0.97) and (current_price <= peak_price * 1.08)

        # 條件 3：中期趨勢向上，站上 60MA
        ma60 = recent_df["ma60"].iloc[-1]
        is_above_ma60 = current_price > ma60

        if is_w_shape and is_breakout and is_above_ma60:
            return True, peak_price, min(l1_price, l2_price)

        return False, 0, 0
    except:
        return False, 0, 0

# ==========================================
# 💰 進出場策略與風控水位
# ==========================================
def trade_levels(price, low_price, neckline):
    stop = low_price * 0.98                 # 停損設在雙底最低點下方 2%
    target = neckline + (neckline - low_price) # 目標價：頸線加上W底高度
    return round(price, 2), round(stop, 2), round(target, 2)

# ==========================================
# 🎨 轉折 K 線圖繪製模組
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
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart['60MA'] = df_chart['Close'].rolling(window=60).mean()

    df_chart['Close'] = pd.to_numeric(df_chart['Close'], errors='coerce')
    df_chart['High'] = pd.to_numeric(df_chart['High'], errors='coerce')
    df_chart['Low'] = pd.to_numeric(df_chart['Low'], errors='coerce')

    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA', '60MA']).copy()

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

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 5MA 轉折波段圖")
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
            <span style="color: #9C27B0; margin-right: 15px;">20MA: {get_ma_details('20MA')}</span>
            <span style="color: #009688;">60MA: {get_ma_details('60MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

    plots = [
        mpf.make_addplot(df_chart['5MA'], color='orange', width=1),
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
if st.button("🚀 執行W底策略選股"):
    results = []
    batch_size = 150  
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    status_text = st.empty()

    for i in range(total_batches):
        status_text.text(f"正在掃描市場W底型態... 進度：{i+1}/{total_batches} 批次")
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

                if df.empty or len(df) < 90:
                    continue

                df = add_indicators(df)
                price = df["Close"].iloc[-1]
                volume = df["Volume"].iloc[-1]
                
                volume_sheets = volume / 1000 
                if volume_sheets < 500:
                    continue

                is_w, neckline, low_price = check_w_bottom(df)
                if not is_w:
                    continue

                entry, stop, target = trade_levels(price, low_price, neckline)

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "當日收盤": round(price, 2),
                    "頸線壓力": round(neckline, 2),
                    "成交量(張)": int(volume_sheets),
                    "建議進場": entry,
                    "防守停損": stop,
                    "波段目標": target
                })
            except:
                continue
        progress.progress((i + 1) / total_batches)
    
    status_text.text("🎉 W底策略選股完成！")

    if not results:
        st.warning("⚠️ 經過成交量（500張）與W底型態限制篩選後，目前沒有符合標準的標的。")
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
    st.subheader(f"📊 W底策略精選總名單（共 {len(saved_df)} 檔）")
    
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
