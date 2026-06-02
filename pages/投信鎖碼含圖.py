import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（平衡實戰版）")

# --- 1. 狀態持久化 ---
if 'out' not in st.session_state:
    st.session_state.out = pd.DataFrame()

# --- 2. 轉折 K 線圖繪製模組 ---
def draw_zigzag_chart(ticker_code, stock_name):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name} 的數據。")
        return

    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()
    
    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()
    
    zigzag_points = []
    grouped = df_chart.groupby('State_Group')
    for g_id in sorted(df_chart['State_Group'].unique()):
        if g_id <= 2: continue
        group_data = grouped.get_group(g_id)
        if group_data['State'].iloc[0] == 1:
            h_idx = group_data['High'].idxmax()
            zigzag_points.append((df_chart.index.get_loc(h_idx), df_chart.loc[h_idx, 'High']))
            df_chart.loc[h_idx, 'Label'] = "H"
        else:
            b_idx = group_data['Low'].idxmin()
            zigzag_points.append((df_chart.index.get_loc(b_idx), df_chart.loc[b_idx, 'Low']))
            df_chart.loc[b_idx, 'Label'] = "B"

    # 繪圖
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df_chart[['5MA', '10MA', '20MA']])]
    fig, axlist = mpf.plot(df_chart, type='candle', style=s_style, addplot=plots, returnfig=True, figsize=(10, 6))
    
    main_ax = axlist[0]
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points)
        main_ax.plot(x, y, color='black', alpha=0.5, linewidth=1.5)
    
    st.pyplot(fig)
    plt.close(fig)

# --- 3. 投信資料抓取 ---
def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except: return None

# --- 4. 主邏輯執行 ---
if st.button("開始 V9.2"):
    with st.spinner("計算鎖碼中..."):
        all_df = []
        today = datetime.today()
        for i in range(60): # 抓取更多天數以利運算
            d = (today - timedelta(days=i)).strftime("%Y%m%d")
            df = get_day(d)
            if df is not None and not df.empty: all_df.append(df)
            time.sleep(0.02)
        
        df = pd.concat(all_df, ignore_index=True)
        # (這裡插入你原本的鎖碼核心邏輯，最後產出 out)
        # 為演示目的，假設產出了 out：
        # out = ... (你的策略運算結果)
        st.session_state.out = out 
        st.rerun()

# --- 5. 互動顯示 ---
if not st.session_state.out.empty:
    out = st.session_state.out
    col1, col2 = st.columns([1, 4])
    with col1:
        selected_stock = st.selectbox("鎖碼股清單:", out['股票'].tolist())
    with col2:
        st.subheader(f"分析標的: {selected_stock}")
        draw_zigzag_chart(f"{selected_stock}.TW", selected_stock)
else:
    st.info("請按下「開始 V9.2」按鈕進行選股。")
