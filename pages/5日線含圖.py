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
# 📦 股票池模組 (自動抓取台股上市/上櫃代號)
# ==========================================
@st.cache_data(ttl=86400)
def get_stock_list():
    """從 twstock 自動獲取台灣上市與上櫃的 4 位數股票代號"""
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                # 上市後綴為 .TW，上櫃後綴為 .TWO
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
# 📈 技術指標計算
# ==========================================
def add_indicators(df):
    """計算策略所需的技術指標"""
    df = df.copy()
    df["ma5"] = df["Close"].rolling(5).mean()
    df["ma10"] = df["Close"].rolling(10).mean()
    df["ma20"] = df["Close"].rolling(20).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    return df

# ==========================================
# 💯 因子多頭評分模型
# ==========================================
def score(price, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    """根據多頭排列、量能與當日漲跌進行綜合評分（最高 7 分）"""
    s = 0
    s += 2 if price > ma5 else 0
    s += 1 if ma5 > ma10 else 0
    s += 1 if ma10 > ma20 else 0
    s += 2 if vol > vol_ma5 else 0
    s += 1 if change_pct > 0 else 0
    return s

# ==========================================
# 🎯 四池分類邏輯（嚴格排他性與型態優化）
# ==========================================
def classify_pool(s, df, price, ma5, ma10, ma20, open_price):
    """將滿足條件的股票精準分類至一到四池"""
    try:
        if df is None or df.empty or len(df) < 30:
            return None

        ma20_series = df["ma20"]
        above_ma20 = price > ma20
        ma20_up = ma20_series.iloc[-1] > ma20_series.iloc[-5]  # MA20 趨勢上揚
        trend_align = (ma5 > ma10 > ma20)                      # 均線多頭排列
        red_k = price > open_price                             # 當日收紅K
        vol_ok = df["Volume"].iloc[-1] > df["vol_ma5"].iloc[-1]  # 今日爆量
        accel = df["Close"].pct_change().tail(3).mean() > 0     # 近3日漲速加速

        # 🔴 第四池：極強勢主升段 (高分 + 均線多頭排列 + 趨勢加速 + 量能達標)
        if ma20_up and above_ma20 and trend_align and accel and vol_ok and s >= 6:
            return "🔴 第四池"

        # 🔵 第三池：強勢高檔震盪 (均線多頭排列 + 過去10天強勢貼著MA5 + 分數中高)
        if ma20_up and above_ma20 and trend_align and s >= 5:
            not_early = (df["Close"].iloc[-10:] > df["ma5"].iloc[-10:]).all()
            if not_early:
                return "🔵 第三池"

        # 🟠 第二池：標準多頭起漲 (均線多頭排列 + 基礎分達標)
        if ma20_up and above_ma20 and trend_align and s >= 4:
            return "🟠 第二池"

        # 🟡 第一池：跌深轉強/均線修正後突破過前高
        if len(df) >= 15:
            # 過去 15 天（不含今天）曾經跌破過 MA5
            was_below_ma5 = (df["Close"].iloc[-15:-1] < df["ma5"].iloc[-15:-1]).any()
            reclaim_ma5 = price > ma5
            prev_high_break = price > df["High"].iloc[-2]  # 強勢突破昨日高點

            if ma20_up and above_ma20 and was_below_ma5 and reclaim_ma5 and red_k and prev_high_break:
                return "🟡 第一池"

        return None
    except:
        return None

# ==========================================
# 💰 進出場策略與風控水位
# ==========================================
def trade_levels(price, ma5, ma10, pool):
    """根據不同池別的特性，給予不同的停損與目標價配置"""
    if pool == "🔴 第四池":
        stop = ma10             # 強勢股不深回，以 MA10 為波段防守
        target = price * 1.25   # 目標期待 +25%
    elif pool == "🔵 第三池":
        stop = ma5              # 極端沿線飆股，跌破 MA5 即出場
        target = price * 1.20   # 目標期待 +20%
    elif pool == "🟠 第二池":
        stop = ma5              # 標準多頭起漲，防守 MA5
        target = price * 1.15   # 目標期待 +15%
    else: # 🟡 第一池
        stop = ma10             # 破底翻策略，給予較大震盪空間防守 MA10
        target = price * 1.10   # 目標期待 +10%
    return round(price, 2), round(stop, 2), round(target, 2)


# ==========================================
# 🎨 轉折 K 線圖繪製模組 (設定為 3 個月區間)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    """繪製 3 個月區間的 5MA 轉折波段圖"""
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d') # 精準 3 個月範圍
    
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    # 處理 yfinance 多國資料庫結構
    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    # 1. 計算均線
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()

    df_chart['Close'] = pd.to_numeric(df_chart['Close'], errors='coerce')
    df_chart['High'] = pd.to_numeric(df_chart['High'], errors='coerce')
    df_chart['Low'] = pd.to_numeric(df_chart['Low'], errors='coerce')

    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()

    # 2. 轉折波段邏輯
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

    # 3. 取得均線數據與箭頭
    def get_ma_details(col_name):
        now = df_chart[col_name].iloc[-1]
        pre = df_chart[col_name].iloc[-2]
        arrow = "▲" if now >= pre else "▼"
        return f"{now:.2f} {arrow}"

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 3個月 5MA 轉折波段圖")
    st.markdown(f"""
        <div style="
            background-color: #f8f9fa; 
            padding: 10px 15px; 
            border-radius: 5px; 
            margin-top: 5px; 
            margin-bottom: 10px; 
            font-family: monospace; 
            font-size: 15px; 
            font-weight: bold;
            border-left: 5px solid #6c757d;
        ">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    # 4. 繪製圖表
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

    plots = [
        mpf.make_addplot(df_chart['5MA'], color='orange', width=1),
        mpf.make_addplot(df_chart['10MA'], color='blue', width=1),
        mpf.make_addplot(df_chart['20MA'], color='purple', width=1)
    ]

    fig, axlist = mpf.plot(
        df_chart, type='candle', style=s_style, addplot=plots, 
        returnfig=True, figsize=(12, 6), volume=True,
        panel_ratios=(4,1)
    )
    
    main_ax = axlist[0]

    # 5. 連接轉折線
    if len(zigzag_points) > 1:
        x_coords, y_coords = zip(*zigzag_points)
        main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

    # 6. 標註 H/B
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
# 🚀 盤後選股功能 (包含 800張放寬量 + 8%防追高)
# ==========================================
if st.button("🚀 執行盤後策略選股"):
    results = []
    batch_size = 150  # 批次包裝，防止請求過快被 Yahoo Finance 封鎖
    total_batches = (len(tickers) + batch_size - 1) // batch_size
    progress = st.progress(0)
    status_text = st.empty()

    for i in range(total_batches):
        status_text.text(f"正在掃描市場股票... 進度：{i+1}/{total_batches} 批次")
        batch = tickers[i * batch_size:(i + 1) * batch_size]
        
        try:
            data = yf.download(tickers=batch, period="3mo", interval="1d", group_by="ticker", progress=False, threads=True)
        except Exception as e:
            continue

        for t in batch:
            try:
                # 兼容 yfinance 多股與單股下載時的 MultiIndex 結構
                if len(batch) > 1:
                    if t in data.columns.levels[0]:
                        df = data[t].dropna(subset=["Close"])
                    else:
                        continue
                else:
                    df = data.dropna(subset=["Close"])

                if df.empty or len(df) < 30:
                    continue

                # 基礎數據提取
                df = add_indicators(df)
                price = df["Close"].iloc[-1]
                open_price = df["Open"].iloc[-1]
                volume = df["Volume"].iloc[-1]
                
                # 【濾網 1】將總股數換算為台股「張數」
                volume_sheets = volume / 1000 
                
                # 🔥 實戰優化：門檻設為 800 張，確保中小型黑馬股順利通關
                if volume_sheets < 800:
                    continue

                ma5 = df["ma5"].iloc[-1]
                ma10 = df["ma10"].iloc[-1]
                ma20 = df["ma20"].iloc[-1]
                change_pct = (price - df["Close"].iloc[-2]) / df["Close"].iloc[-2]

                s = score(price, ma5, ma10, ma20, volume, df["vol_ma5"].iloc[-1], change_pct)
                pool = classify_pool(s, df, price, ma5, ma10, ma20, open_price)

                if pool is None:
                    continue

                # 計算關鍵價位
                entry, stop, target = trade_levels(price, ma5, ma10, pool)

                # ==========================================
                # 🔥 【濾網 3】安全邊際 / 防追高乖離濾網（8% 限制在線）
                # ==========================================
                risk_pct = (price - stop) / stop
                if risk_pct > 0.08:
                    continue

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "池別": pool,
                    "分數": s,
                    "當日收盤": round(price, 2),
                    "成交量(張)": int(volume_sheets),
                    "建議進場": entry,
                    "防守停損": stop,
                    "波段目標": target
                })
            except:
                continue
        progress.progress((i + 1) / total_batches)
    
    status_text.text("🎉 精煉選股完成！")

    # 輸出選股結果至頁面與 Session State 暫存器
    if not results:
        st.warning("⚠️ 經過成交量（800張）與防追高限制（8%）篩選後，目前沒有符合標準的標的。")
        for pool_name in ["🔴 第四池", "🔵 第三池", "🟠 第二池", "🟡 第一池"]:
            st.session_state[f"pool_{pool_name}"] = pd.DataFrame()
    else:
        df_res = pd.DataFrame(results)
        for pool_name in ["🔴 第四池", "🔵 第三池", "🟠 第二池", "🟡 第一池"]:
            sub_df = df_res[df_res["池別"] == pool_name]
            st.session_state[f"pool_{pool_name}"] = sub_df # 將包含 ticker 欄位的完整資料寫入暫存


# ==========================================
# 📊 畫面渲染模組與【點擊看轉折圖互動機制】
# ==========================================
for pool_name in ["🔴 第四池", "🔵 第三池", "🟠 第二池", "🟡 第一池"]:
    if f"pool_{pool_name}" in st.session_state:
        saved_df = st.session_state[f"pool_{pool_name}"]
        st.subheader(f"📊 策略精選名單 - {pool_name}")
        
        if not saved_df.empty:
            # 呈現給使用者看的前台表格：自動依照「成交量(張)」由大到小排序，並將圖表用的後台 ticker 隱藏
            display_df = saved_df.sort_values(by="成交量(張)", ascending=False).drop(columns=["ticker"])
            st.dataframe(display_df, use_container_width=True)
            
            # 🎯 點擊選股連動：為該池生成專屬的下拉式連動選單
            stock_options = [f"{row['代號']} {row['名稱']}" for _, row in saved_df.iterrows()]
            selected_stock = st.selectbox(
                f"🔍 點擊選擇【{pool_name}】中的股票代號查看 3個月轉折圖:", 
                ["請選擇..."] + stock_options, 
                key=f"select_{pool_name}"
            )
            
            if selected_stock != "請選擇...":
                selected_code = selected_stock.split(" ")[0]
                selected_name = selected_stock.split(" ")[1]
                # 撈出對應的正確 yfinance 後綴
                target_ticker = saved_df[saved_df["代號"] == selected_code]["ticker"].values[0]
                
                # 繪製圖形
                draw_zigzag_chart(target_ticker, selected_name)
        else:
            st.info("此池目前無符合條件股票")


# ==========================================
# 📈 盤中即時監控模組 (批次極速刷新)
# ==========================================
st.markdown("---")
st.subheader("📈 盤中動態監控系統（連動盤後選股名單）")

def run_monitor_optimized(pool_df):
    """將選出的名單進行盤中批次即時價位下載與突破訊號判斷"""
    if pool_df.empty:
        return pd.DataFrame()
    
    monitor_tickers = pool_df["ticker"].tolist()
    
    try:
        # 盤中同樣採批次打包下載，阻絕迴圈卡死
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

            # 讀取盤中最新 K 線數據
            open_now = df["Open"].iloc[-1]
            close_now = df["Close"].iloc[-1]
            ma5 = df["Close"].rolling(5).mean().iloc[-1]
            
            # 近 5 日最高價（排除今日盤中，避免自我實現的突破）
            high_5 = df["High"].iloc[-6:-1].max()
            
            vol_today = df["Volume"].iloc[-1]
            vol_avg = df["Volume"].rolling(5).mean().iloc[-1]

            # 訊號旗標計算
            red_k = close_now > open_now
            above_ma5 = close_now > ma5
            breakout = close_now > high_5
            vol_ok = vol_today > vol_avg

            # 決定盤中即時訊號
            if red_k and above_ma5 and vol_ok and breakout:
                signal = "🟢 強力BUY (量價齊揚突破)"
            elif red_k and above_ma5:
                signal = "🟡 WATCH (常態轉強)"
            else:
                signal = "🔴 NO (型態轉弱/收黑)"

            live_results.append({
                "代號": row["代號"],
                "名稱": row["名稱"],
                "池別": row["池別"],
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
    # 檢查防呆機制：確保用戶已經跑過盤後選股
    if "pool_🟡 第一池" not in st.session_state:
        st.warning("⚠️ 請先在上方點擊「🚀 執行盤後策略選股」以建立今日的基礎監控名單。")
        st.stop()

    # 採用 2x2 的優雅區塊佈局呈現盤中訊號
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    pools_config = [
        ("🟡 第一池", col1), 
        ("🟠 第二池", col2), 
        ("🔵 第三池", col3), 
        ("🔴 第四池", col4)
    ]

    for p_name, col in pools_config:
        with col:
            st.markdown(f"### {p_name} 監控中")
            saved_df = st.session_state.get(f"pool_{p_name}", pd.DataFrame())
            
            if not saved_df.empty:
                res_df = run_monitor_optimized(saved_df)
                if not res_df.empty:
                    st.dataframe(res_df, use_container_width=True)
                else:
                    st.info("暫無有效即時數據")
            else:
                st.info("ℹ️ 此池無基礎選股標的，盤中跳過監控。")
