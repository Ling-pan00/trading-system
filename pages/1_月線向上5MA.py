import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np

# 設定 Streamlit 頁面配置
st.set_page_config(page_title="四池量化 Pro v2.2", layout="wide")
st.title("📊 四池量化交易系統 Pro v2.2（效能與邏輯完整版）")

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
        trend_align = (ma5 > ma10 > ma20)                       # 均線多頭排列
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
# 🚀 盤後選股功能 (效能優化批次下載)
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
            # 批次打包下載，大幅縮短執行時間
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

                # 計算指標與評分
                df = add_indicators(df)
                price = df["Close"].iloc[-1]
                open_price = df["Open"].iloc[-1]
                ma5 = df["ma5"].iloc[-1]
                ma10 = df["ma10"].iloc[-1]
                ma20 = df["ma20"].iloc[-1]
                change_pct = (price - df["Close"].iloc[-2]) / df["Close"].iloc[-2]

                s = score(price, ma5, ma10, ma20, df["Volume"].iloc[-1], df["vol_ma5"].iloc[-1], change_pct)
                pool = classify_pool(s, df, price, ma5, ma10, ma20, open_price)

                if pool is None:
                    continue

                # 計算關鍵價位
                entry, stop, target = trade_levels(price, ma5, ma10, pool)

                results.append({
                    "代號": ticker_map[t]["code"],
                    "名稱": ticker_map[t]["name"],
                    "ticker": t,
                    "池別": pool,
                    "分數": s,
                    "當日收盤": round(price, 2),
                    "建議進場": entry,
                    "防守停損": stop,
                    "波段目標": target
                })
            except:
                continue
        progress.progress((i + 1) / total_batches)
    
    status_text.text("🎉 全市場掃描完成！")

    # 輸出選股結果至頁面與 Session State
    if not results:
        st.warning("⚠️ 當前市場環境下，沒有符合四池篩選條件的股票。")
    else:
        df_res = pd.DataFrame(results)
        
        # 依序渲染四個池子的表格
        for pool_name in ["🔴 第四池", "🔵 第三池", "🟠 第二池", "🟡 第一池"]:
            st.subheader(f"📊 策略選股名單 - {pool_name}")
            sub_df = df_res[df_res["池別"] == pool_name].drop(columns=["ticker"])
            
            if not sub_df.empty:
                st.dataframe(sub_df, use_container_width=True)
            else:
                st.info("此池目前無符合條件股票")
            
            # 將完整含 ticker 的 DataFrame 存入 session_state 供盤中監控連動
            st.session_state[f"pool_{pool_name}"] = df_res[df_res["池別"] == pool_name]


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
            
            # 關鍵修正：近 5 日最高價（排除今日盤中，避免自我實現的突破）
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
