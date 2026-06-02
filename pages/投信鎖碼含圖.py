import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import requests
import time
from datetime import datetime, timedelta

# --- 1. 您的篩選核心邏輯 (完全保留) ---
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

def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty: all_df.append(df)
        time.sleep(0.05)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 2. 您的轉折 K 線圖繪製模組 (完全原樣保留) ---
def draw_zigzag_chart(ticker_code, stock_name):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # 自動處理上市櫃代號 (您原來的邏輯)
    ticker = f"{ticker_code}.TW" if int(ticker_code) < 2000 else f"{ticker_code}.TWO"
    
    df_chart = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
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
    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()

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

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 3個月 5MA 轉折波段圖")
    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 5px; font-family: monospace; font-size: 15px; font-weight: bold; border-left: 5px solid #6c757d;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df_chart['5MA'], color='orange', width=1), 
             mpf.make_addplot(df_chart['10MA'], color='blue', width=1), 
             mpf.make_addplot(df_chart['20MA'], color='purple', width=1)]

    fig, axlist = mpf.plot(df_chart, type='candle', style=s_style, addplot=plots, returnfig=True, figsize=(12, 6), volume=True, panel_ratios=(4,1))
    main_ax = axlist[0]

    if len(zigzag_points) > 1:
        x_coords, y_coords = zip(*zigzag_points)
        main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

    for idx, row in df_chart[df_chart['Label'].notnull()].iterrows():
        x = df_chart.index.get_loc(idx)
        is_h = row['Label'] == "H"
        main_ax.text(x, row['High' if is_h else 'Low'], row['Label'], color='red' if is_h else 'green', weight='bold', ha='center', va='bottom' if is_h else 'top', bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))

    st.pyplot(fig)
    plt.close(fig)

# --- 3. 完美整合的執行區 ---
st.set_page_config(page_title="投信鎖碼 Pro", layout="wide")
if st.button("開始執行"):
    df = load(30)
    # 防錯：動態尋找欄位
    buy_col = [c for c in df.columns if "買賣超" in str(c)][0]
    stock_col = [c for c in df.columns if "證券代號" in str(c)][0]
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    # 您的原始篩選邏輯
    result = []
    for stock, g in df.groupby(stock_col):
        series = g.sort_values("date")[buy_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    out = pd.DataFrame(result)
    
    st.dataframe(out)
    sel = st.selectbox("選擇股票:", out['股票'].unique())
    if sel: draw_zigzag_chart(sel, sel)
