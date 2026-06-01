import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

# --- 頁面配置 ---
st.set_page_config(page_title="三池強力監控系統", layout="wide")
st.title("🚀 三池強力監控系統")

# --- 1. 工具函式 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

def get_zigzag_points(df):
    df['5MA'] = df['Close'].rolling(5).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    points = []
    for g_id, group in df.groupby('State_Group'):
        if g_id <= 2: continue
        state = group['State'].iloc[0]
        if state == 1:
            idx = group['High'].idxmax()
            points.append((df.index.get_loc(idx), df.loc[idx, 'High'], "H"))
        else:
            idx = group['Low'].idxmin()
            points.append((df.index.get_loc(idx), df.loc[idx, 'Low'], "B"))
    return points

# --- 2. 盤後選股邏輯 ---
if "results" not in st.session_state: st.session_state["results"] = pd.DataFrame()
tickers = [s["ticker"] for s in get_stock_list()]
ticker_map = {s["ticker"]: s for s in get_stock_list()}

if st.button("🚀 執行盤後強力選股"):
    results = []
    with st.spinner("掃描市場動能中..."):
        for t in tickers[:100]:
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if len(df) < 20: continue
                c, ma5 = float(df["Close"].iloc[-1]), df["Close"].rolling(5).mean().iloc[-1]
                pct = float((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                if c > ma5 and pct > 2:
                    results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t})
            except: continue
    st.session_state["results"] = pd.DataFrame(results)

# --- 3. 介面與監控 ---
if not st.session_state["results"].empty:
    # 盤中監控區塊
    st.write("---")
    st.subheader("📈 盤中動能監控")
    if st.button("🔄 更新監控訊號"):
        live_data = []
        for _, row in st.session_state["results"].head(10).iterrows():
            d = yf.download(row["ticker"], period="2d", progress=False)
            if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
            sig = "🟢 強勢" if d["Open"].iloc[-1] > d["Close"].iloc[-2] else "🟡 觀察"
            live_data.append({"代號": row["代號"], "訊號": sig})
        st.dataframe(pd.DataFrame(live_data), use_container_width=True)

    # 轉折圖分析區塊
    st.write("---")
    st.subheader("🎯 轉折監測器")
    sel = st.selectbox("選股分析：", st.session_state["results"]["代號"].tolist())
    ticker = st.session_state["results"][st.session_state["results"]["代號"] == sel]["ticker"].values[0]
    
    df = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['5MA'], df['10MA'], df['20MA'] = df['Close'].rolling(5).mean(), df['Close'].rolling(10).mean(), df['Close'].rolling(20).mean()

    # HTML 均線看板
    def get_ma_details(col):
        now, pre = df[col].iloc[-1], df[col].iloc[-2]
        return f"{now:.2f} {'▲' if now >= pre else '▼'}"

    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    # 繪圖
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df[m], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])]
    fig, axlist = mpf.plot(df, type='candle', style=style, addplot=plots, returnfig=True, figsize=(10, 6), volume=True)
    
    # 轉折標記
    ax = axlist[0]
    points = get_zigzag_points(df)
    for x_pos, val, lbl in points:
        ax.text(x_pos, val, lbl, color='red' if lbl=="H" else 'green', weight='bold', ha='center', 
                bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))
    st.pyplot(fig)
