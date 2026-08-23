import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="一字頂反轉量化選股 Pro", layout="wide")
st.title("📊 一字頂反轉量化交易系統（平頂阻力突破失敗 + 500張量能過濾）")

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
# 🎯 一字頂 (平頂阻力) 策略條件檢查 (已平衡精準度與條件)
# ==========================================
def check_flat_top(df):
    """
    一字頂（平頂阻力）檢測邏輯：
    1. 檢視過去 90 天的高點走勢。
    2. 尋找至少 2 次以上、價格誤差在 2.0% 以內、且間隔 5 天以上的明顯高點。
    3. 現價貼近一字頂阻力區，且跌破 5MA 出現轉弱訊號。
    """
    try:
        if df is None or df.empty or len(df) < 90:
            return False, 0, 0

        recent_df = df.iloc[-90:].copy()
        highs = recent_df["High"].values
        closes = recent_df["Close"].values
        lows = recent_df["Low"].values

        # 尋找顯著的波段高點（左右各 5 天最高）
        peaks = []
        for i in range(5, len(highs)-5):
            if highs[i] == max(highs[i-5:i+6]):
                peaks.append((i, highs[i]))

        if len(peaks) < 2:
            return False, 0, 0

        # 尋找高點群組 (誤差 2.0%，時間間隔至少 5 天)
        flat_resistance = 0
        found = False
        
        for i in range(len(peaks)):
            cluster = [peaks[i]]
            for j in range(i + 1, len(peaks)):
                if peaks[j][0] - cluster[-1][0] >= 5: # 間隔 5 天
                    if abs(peaks[j][1] - cluster[0][1]) / cluster[0][1] <= 0.02: # 誤差 2%
                        cluster.append(peaks[j])
            
            if len(cluster) >= 2:
                flat_resistance = sum([p[1] for p in cluster]) / len(cluster)
                found = True
                break

        if not found:
            return False, 0, 0

        current_price = closes[-1]
        ma5 = recent_df["ma5"].iloc[-1]
        
        # 條件：現價貼近一字頂壓力（阻力價上下 2.5% 內），且跌破 5MA
        is_near_resistance = (current_price >= flat_resistance * 0.975) and (current_price <= flat_resistance * 1.025)
        is_weakening = current_price < ma5

        if is_near_resistance and is_weakening:
            support_price = lows[-30:].min()
            return True, flat_resistance, support_price

        return False, 0, 0
    except:
        return False, 0, 0

# ==========================================
# 💰 進出場策略與風控水位
# ==========================================
def trade_levels(price, resistance, support):
    stop = resistance * 1.02      # 停損設在壓力價上方 2%
    target = support              # 波段目標看下方近期支撐
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
if st.button("🚀 執行一字頂策略選股"):
    results = []
    batch_size = 150  
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    status_text = st.empty()

    for i in range(total_batches):
        status_text.text(f"正在掃描市場一字頂型態... 進度：{i+1}/{total_batches} 批次")
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

                is_flat, resistance, support = check_flat_top(df)
                if not is_flat:
                    continue

                entry, stop, target = trade_levels(price, resistance, support)

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "當日收盤": round(price, 2),
                    "一字頂壓力": round(resistance, 2),
                    "成交量(張)": int(volume_sheets),
                    "建議進場": entry,
                    "防守停損": stop,
                    "波段目標": target
                })
            except:
                continue
        progress.progress((i + 1) / total_batches)
    
    status_text.text("🎉 一字頂策略選股完成！")

    if not results:
        st.warning("⚠️ 經過一字頂型態與成交量限制篩選後，目前沒有符合標準的標的。")
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
    st.subheader(f"📊 一字頂策略精選總名單（共 {len(saved_df)} 檔）")
    
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
