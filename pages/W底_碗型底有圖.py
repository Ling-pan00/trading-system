import streamlit as st
import twstock
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import concurrent.futures
from datetime import datetime, timedelta

# --- 1. 選股器核心邏輯 ---
@st.cache_data(ttl=3600)
def get_stock_df_twstock(code):
    try:
        stock = twstock.Stock(code)
        data = stock.fetch_31()
        if not data or len(data) < 30: return None
        return pd.DataFrame(data)
    except: return None

def analyze_w_bottom(code):
    df = get_stock_df_twstock(code)
    if df is None: return None
    close, volume = df['close'].values, df['capacity'].values
    ma20 = np.mean(close[-20:])
    if close[-1] < ma20: return None
    min_price = min(close[-20:])
    avg_vol = np.mean(volume[-20:])
    if abs(close[-1] - min_price) / min_price < 0.05 and volume[-1] > (avg_vol * 1.2):
        return True
    return None

# --- 2. 波段繪圖邏輯 ---
@st.cache_data
def get_yfinance_data(stock_code):
    end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    for ticker in [f"{stock_code}.TW", f"{stock_code}.TWO"]:
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if not df.empty: return df
    return None

def plot_zigzag_chart(df):
    df['5MA'] = df['Close'].rolling(5).mean()
    df['10MA'] = df['Close'].rolling(10).mean()
    df['20MA'] = df['Close'].rolling(20).mean()
    df = df.dropna().copy()
    
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    change_indices = df.index[df['State'] != df['State'].shift()].tolist()
    if df.index[-1] not in change_indices: change_indices.append(df.index[-1])
    
    df['Label'] = None
    zigzag_points = []
    for i in range(len(change_indices) - 1):
        subset = df.loc[change_indices[i]:change_indices[i+1]]
        if subset['State'].iloc[0] == 1:
            idx = subset['High'].idxmax()
            df.at[idx, 'Label'] = "H"
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
        else:
            idx = subset['Low'].idxmin()
            df.at[idx, 'Label'] = "B"
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))
            
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    ap = [mpf.make_addplot(df['5MA'], color='orange', width=0.8),
          mpf.make_addplot(df['10MA'], color='black', width=0.8),
          mpf.make_addplot(df['20MA'], color='purple', width=0.8)]
    
    fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(12, 7), volume=True)
    main_ax = axlist[0]
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points)
        main_ax.plot(x, y, color='#2196F3', alpha=0.7, linewidth=1.5, zorder=3)
    for idx, row in df[df['Label'].notnull()].iterrows():
        x = df.index.get_loc(idx)
        val = row['High'] if row['Label'] == "H" else row['Low']
        main_ax.annotate(row['Label'], xy=(x, val), xytext=(0, 15 if row['Label'] == "H" else -25), textcoords='offset points', ha='center', color='red' if row['Label'] == "H" else 'green', weight='bold')
    return fig

# --- 3. UI 介面 ---
st.title("📈 底部選股 + 5MA 轉折分析系統")
selected_industry = st.selectbox("請選擇產業：", ["半導體業", "光電業", "電子零組件業"]) # 可自行擴充
if st.button("🚀 開始掃描"):
    target_list = [code for code, info in twstock.codes.items() if info.group == selected_industry]
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        for code, result in zip(target_list, executor.map(analyze_w_bottom, target_list)):
            if result: found.append(code)
    
    if found:
        st.success(f"找到 {len(found)} 檔符合標的")
        selected_code = st.selectbox("選擇要查看的股票：", found)
        df_chart = get_yfinance_data(selected_code)
        if df_chart is not None:
            st.pyplot(plot_zigzag_chart(df_chart))
    else: st.info("無符合標的")
