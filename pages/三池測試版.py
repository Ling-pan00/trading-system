import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import datetime

# 設定頁面為寬螢幕版面
st.set_page_config(page_title="三池獨立監控系統", layout="wide")

st.title("📊 三池獨立交易監控系統 Pro ✖ 轉折波段連線")

# =========================
# 股票池
# =========================
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

st.write(f"📦 股票數：{len(tickers)}")


# =========================
# 評分
# =========================
def score(close, ma5, ma10, ma20, vol, vol_ma5, change_pct):
    s = 0
    if close > ma5:
        s += 2
    if ma5 > ma10:
        s += 1
    if ma10 > ma20:
        s += 1
    if vol > vol_ma5:
        s += 2
    if change_pct > 0:
        s += 1
    return s


# =========================
# 三池分類
# =========================
def classify_pool(score):
    if score >= 5:
        return "🚀 突破股"
    elif score >= 3:
        return "🟡 動能股"
    else:
        return "🧊 回檔股"


# =========================
# 盤中訊號
# =========================
def intraday_signal(open_p, close_y, low_y, high_y, vol, vol_y):
    strong = open_p >= close_y
    hold = open_p >= low_y
    vol_ok = vol >= vol_y * 0.7
    breakout = open_p > high_y

    if strong and hold and vol_ok:
        if breakout:
            return "🟢 BUY（追強）"
        return "🟢 BUY（回測）"
    if hold:
        return "🟡 WATCH"
    return "🔴 NO"


# =========================
# 盤後掃描
# =========================
if st.button("🚀 盤後選股"):
    results = []
    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    progress = st.progress(0)
    status = st.empty()

    for i in range(total_batches):
        batch = tickers[i*batch_size:(i+1)*batch_size]
        status.text(f"📥 {i+1}/{total_batches}")

        try:
            data = yf.download(
                tickers=batch,
                period="3mo",
                interval="1d",
                group_by="ticker",
                progress=False,
                threads=True
            )

            for t in batch:
                try:
                    df_s = data[t]
                    if df_s.empty:
                        continue

                    close = df_s["Close"]
                    volume = df_s["Volume"]

                    if len(close) < 20:
                        continue

                    ma5 = close.rolling(5).mean().iloc[-1]
                    ma10 = close.rolling(10).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]
                    vol_ma5 = volume.rolling(5).mean().iloc[-1]
                    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

                    s = score(
                        close.iloc[-1], ma5, ma10, ma20,
                        volume.iloc[-1], vol_ma5, change_pct
                    )
                    pool = classify_pool(s)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "ticker": t,
                        "分數": s,
                        "池別": pool,
                        "收盤": float(close.iloc[-1])
                    })
                except:
                    continue
        except:
            continue

        progress.progress((i+1)/total_batches)

    status.text("✅ 完成")

    if results:
        df = pd.DataFrame(results)
        st.session_state["breakout"] = df[df["池別"] == "🚀 突破股"].sort_values("分數", ascending=False).head(5)
        st.session_state["momentum"] = df[df["池別"] == "🟡 動能股"].sort_values("分數", ascending=False).head(5)
        st.session_state["pullback"] = df[df["池別"] == "🧊 回檔股"].sort_values("分數", ascending=False).head(5)


# =========================================================================
# 顯示選股成果 (超乾淨連動版 - 移除雜亂按鈕框框)
# =========================================================================
if "breakout" in st.session_state:
    st.markdown("💡 **提示：下方已為您自動選出三大池最強前 5 檔，請使用最下方的看盤監測器直接切換 K 線圖。**")
    
    # 建立三欄並排展示表格，畫面乾乾淨淨
    p_col1, p_col2, p_col3 = st.columns(3)
    
    with p_col1:
        st.subheader("🚀 突破股 Top5")
        st.dataframe(
            st.session_state["breakout"][["代號", "名稱", "分數", "收盤"]], 
            use_container_width=True, 
            hide_index=True
        )

    with p_col2:
        st.subheader("🟡 動能股 Top5")
        st.dataframe(
            st.session_state["momentum"][["代號", "名稱", "分數", "收盤"]], 
            use_container_width=True, 
            hide_index=True
        )

    with p_col3:
        st.subheader("🧊 回檔股 Top5")
        st.dataframe(
            st.session_state["pullback"][["代號", "名稱", "分數", "收盤"]], 
            use_container_width=True, 
            hide_index=True
        )


# =========================
# 盤中監控（獨立三池）
# =========================
st.write("---")
st.subheader("📈 盤中三池監控")

def run_monitor(df):
    live = []
    for _, row in df.iterrows():
        try:
            t = row["ticker"]
            data = yf.download(t, period="5d", interval="1d", progress=False)

            close = data["Close"]
            volume = data["Volume"]
            open_p = data["Open"]
            high = data["High"]
            low = data["Low"]

            open_now = open_p.iloc[-1]
            close_y = close.iloc[-2]
            low_y = low.min()
            high_y = high.max()

            vol = volume.iloc[-1]
            vol_y = volume.rolling(5).mean().iloc[-1]

            sig = intraday_signal(open_now, close_y, low_y, high_y, vol, vol_y)

            live.append({
                "代號": row["代號"],
                "名稱": row["名稱"],
                "池別": row["池別"],
                "分數": row["分數"],
                "訊號": sig
            })
        except:
            continue
    return pd.DataFrame(live)


if st.button("🔄 更新盤中監控"):
    if "breakout" not in st.session_state:
        st.warning("請先盤後選股")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("### 🚀 突破股監控")
            st.dataframe(run_monitor(st.session_state["breakout"]), use_container_width=True, hide_index=True)
        with col2:
            st.markdown("### 🟡 動能股監控")
            st.dataframe(run_monitor(st.session_state["momentum"]), use_container_width=True, hide_index=True)
        with col3:
            st.markdown("### 🧊 回檔股監控")
            st.dataframe(run_monitor(st.session_state["pullback"]), use_container_width=True, hide_index=True)


# =========================================================================
# 🎯 核心功能：選股池連動轉折 K 線圖 (自動動態鎖定「最近半年」)
# =========================================================================
st.write("---")
st.subheader("🎯 智慧選股連動看盤監測器")

if "breakout" in st.session_state:
    pool_all = pd.concat([
        st.session_state["breakout"], 
        st.session_state["momentum"], 
        st.session_state["pullback"]
    ]).drop_duplicates(subset=['ticker'])
    
    # 自動打包 15 檔股票供下拉選單選擇
    options = [f"{row['代號']} - {row['名稱']} ({row['池別']})" for _, row in pool_all.iterrows()]
    
    selected_option = st.selectbox(
        "👉 請選擇您想觀察的精選策略股：", 
        options
    )
    
    sel_code = selected_option.split(" - ")[0]
    sel_ticker = pool_all[pool_all["代號"] == sel_code]["ticker"].values[0]
    sel_name = pool_all[pool_all["代號"] == sel_code]["名稱"].values[0]
    
    # 自動計算包含今天在內，往前推半年的日期範圍
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=180)

    try:
        with st.spinner(f'正在分析 {sel_code} {sel_name} 最近半年的轉折波浪軌跡...'):
            df_k = yf.download(sel_ticker, start=start_date, end=end_date, progress=False)
            
        if not df_k.empty:
            if isinstance(df_k.columns, pd.MultiIndex):
                df_k.columns = df_k.columns.get_level_values(0)

            df_k['5MA'] = df_k['Close'].rolling(window=5).mean()
            df_k['Close'] = pd.to_numeric(df_k['Close'].iloc[:, 0] if isinstance(df_k['Close'], pd.DataFrame) else df_k['Close'], errors='coerce')
            df_k['High'] = pd.to_numeric(df_k['High'].iloc[:, 0] if isinstance(df_k['High'], pd.DataFrame) else df_k['High'], errors='coerce')
            df_k['Low'] = pd.to_numeric(df_k['Low'].iloc[:, 0] if isinstance(df_k['Low'], pd.DataFrame) else df_k['Low'], errors='coerce')
            df_k['5MA'] = pd.to_numeric(df_k['5MA'], errors='coerce')
            df_k = df_k.dropna(subset=['Close', '5MA']).copy()

            df_k['State'] = np.where(df_k['Close'] > df_k['5MA'], 1, -1)
            df_k['State_Group'] = (df_k['State'] != df_k['State'].shift()).cumsum()

            df_k['Label_Text'] = ""
            df_k['Label_Pos'] = np.nan
            zigzag_points = []

            grouped_k = df_k.groupby('State_Group')
            group_ids_k = sorted(df_k['State_Group'].unique())

            for g_id in group_ids_k:
                group_data = grouped_k.get_group(g_id)
                state = group_data['State'].iloc[0]
                if g_id <= 2:
                    continue
                    
                if state == 1:
                    highest_idx = group_data['High'].idxmax()
                    x_pos = df_k.index.get_loc(highest_idx)
                    y_pos = df_k.loc[highest_idx, 'High']
                    zigzag_points.append((x_pos, y_pos))
                    df_k.loc[highest_idx, 'Label_Text'] = "H"
                    df_k.loc[highest_idx, 'Label_Pos'] = y_pos * 1.015
                elif state == -1:
                    lowest_idx = group_data['Low'].idxmin()
                    x_pos = df_k.index.get_loc(lowest_idx)
                    y_pos = df_k.loc[lowest_idx, 'Low']
                    zigzag_points.append((x_pos, y_pos))
                    df_k.loc[lowest_idx, 'Label_Text'] = "B"
                    df_k.loc[lowest_idx, 'Label_Pos'] = y_pos * 0.985

            mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
            s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
            plots = [mpf.make_addplot(df_k['5MA'], color='orange', width=1.2, label='5MA')]

            fig, axlist = mpf.plot(
                df_k, type='candle', style=s, addplot=plots, 
                returnfig=True, figsize=(14, 6), volume=True
            )
            main_ax = axlist[0]

            if len(zigzag_points) > 1:
                x_coords, y_coords = zip(*zigzag_points)
                main_ax.plot(x_coords, y_coords, color='#666666', linestyle='-', linewidth=2.5, zorder=3)

            for idx, row in df_k[df_k['Label_Text'] != ""].iterrows():
                x_pos = df_k.index.get_loc(idx)
                color = 'red' if row['Label_Text'] == "H" else 'green'
                main_ax.text(
                    x_pos, row['Label_Pos'], row['Label_Text'], 
                    color=color, fontsize=9, weight='bold', ha='center', va='center', zorder=5,
                    bbox=dict(boxstyle="round,pad=0.2", fc="#FFFFCC", alpha=0.9, ec=color, lw=1)
                )

            st.pyplot(fig)
    except Exception as chart_err:
        st.error(f"K線轉換分析失敗: {chart_err}")
else:
    st.info("💡 提示：請先點擊上方的『🚀 盤後選股』按鈕生成三大池股票清單。")
