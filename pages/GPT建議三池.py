import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock

# --- 設定 ---
st.set_page_config(page_title="三池強力監控系統 Pro", layout="wide")
st.title("🚀 三池強力監控系統 Pro")

# --- 1. 資料處理與選股函式 ---
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []
    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"] and len(code) == 4 and code.isdigit():
            ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
            stocks.append({"code": code, "name": info.name, "ticker": ticker})
    return stocks

# --- 2. 選股邏輯 ---
if "results" not in st.session_state: st.session_state["results"] = pd.DataFrame()
tickers = [s["ticker"] for s in get_stock_list()]
ticker_map = {s["ticker"]: s for s in get_stock_list()}

if st.button("🚀 執行強力選股"):
    results = []
    with st.spinner("掃描市場動能中..."):
        for t in tickers[:150]:
            try:
                df = yf.download(t, period="3mo", progress=False)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if len(df) < 20: continue
                # 簡單選股邏輯
                c, ma5 = float(df["Close"].iloc[-1]), df["Close"].rolling(5).mean().iloc[-1]
                pct = float((df["Close"].iloc[-1] - df["Close"].iloc[-2]) / df["Close"].iloc[-2] * 100)
                if c > ma5 and pct > 0:
                    results.append({"代號": ticker_map[t]["code"], "名稱": ticker_map[t]["name"], "ticker": t})
            except: continue
    st.session_state["results"] = pd.DataFrame(results)

# --- 3. 監控與繪圖 (整合你成功的邏輯) ---
if not st.session_state["results"].empty:
    st.subheader("🎯 轉折監測器")
    sel = st.selectbox("選擇個股：", st.session_state["results"]["代號"].tolist())
    ticker = st.session_state["results"][st.session_state["results"]["代號"] == sel]["ticker"].values[0]
    
    df = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 計算均線與轉折
    df['5MA'] = df['Close'].rolling(5).mean()
    df['10MA'] = df['Close'].rolling(10).mean()
    df['20MA'] = df['Close'].rolling(20).mean()
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    
    # 標註 H/B 邏輯
    df['Label'] = None
    zigzag_points = []
    for g_id, group in df.groupby('State_Group'):
        if g_id <= 2: continue
        if group['State'].iloc[0] == 1:
            idx = group['High'].idxmax()
            df.at[idx, 'Label'] = "H"
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
        else:
            idx = group['Low'].idxmin()
            df.at[idx, 'Label'] = "B"
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

    # 【HTML 看板】
    def get_ma_info(col):
        now, pre = df[col].iloc[-1], df[col].iloc[-2]
        return f"{now:.2f} {'▲' if now >= pre else '▼'}"

    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_info('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_info('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_info('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    # 【繪圖】
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df[m], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])]
    
    fig, axlist = mpf.plot(df, type='candle', style=style, addplot=plots, returnfig=True, figsize=(10, 6), volume=True)
    ax = axlist[0]
    
    # 繪製轉折線與標記
    if len(zigzag_points) > 1:
        ax.plot(*zip(*zigzag_points), color='black', alpha=0.5, linewidth=1.5, zorder=3)
    for idx, row in df[df['Label'].notnull()].iterrows():
        is_h = row['Label'] == "H"
        ax.text(df.index.get_loc(idx), row['High' if is_h else 'Low'], row['Label'],
                color='red' if is_h else 'green', weight='bold', ha='center',
                bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))
    
    st.pyplot(fig)
