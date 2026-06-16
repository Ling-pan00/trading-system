import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import requests
import io
from datetime import datetime, timedelta

st.set_page_config(page_title="200檔股票轉折波段系統", layout="wide")
st.title("📈 200檔個股轉折自動標註系統")

# 爬蟲函數 - 使用 BytesIO 解決 No such file 錯誤
@st.cache_data(ttl=3600)
def get_yahoo_ranking(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        # 轉換為 BytesIO 物件，徹底避免將 HTML 解析為檔案路徑的錯誤
        html_stream = io.BytesIO(res.content)
        dfs = pd.read_html(html_stream, flavor='lxml')
        return dfs[0] if dfs else None
    except Exception as e:
        st.error(f"解析網頁失敗，請稍後再試。錯誤代碼: {e}")
        return None

# 初始化股票清單
if 'stock_list' not in st.session_state:
    with st.spinner('正在從 Yahoo 獲取 200 檔排行資料...'):
        up_df = get_yahoo_ranking("https://tw.stock.yahoo.com/rank/change-up/")
        down_df = get_yahoo_ranking("https://tw.stock.yahoo.com/rank/change-down/")
        
        all_stocks = []
        for df, label in [(up_df, "漲幅"), (down_df, "跌幅")]:
            if df is not None and '代號' in df.columns:
                for s in df['代號'].astype(str).tolist():
                    all_stocks.append(f"{s.split('.')[0]} ({label})")
        st.session_state.stock_list = all_stocks

# 介面選擇
selected = st.selectbox("請選擇個股:", st.session_state.stock_list)
stock_code = selected.split(' ')[0]

@st.cache_data
def load_data(ticker):
    end = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    for suffix in [".TW", ".TWO"]:
        df = yf.download(f"{ticker}{suffix}", start=start, end=end, auto_adjust=True)
        if not df.empty: return df
    return None

# 繪圖主邏輯
if stock_code:
    df = load_data(stock_code)
    if df is not None and len(df) > 10:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna().copy()

        # 波段邏輯
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        change_indices = df.index[df['State'] != df['State'].shift()].tolist()
        
        zigzag_points = []
        for i in range(len(change_indices) - 1):
            subset = df.loc[change_indices[i]:change_indices[i+1]]
            idx = subset['High'].idxmax() if subset['State'].iloc[0] == 1 else subset['Low'].idxmin()
            val = subset['High'].max() if subset['State'].iloc[0] == 1 else subset['Low'].min()
            zigzag_points.append((df.index.get_loc(idx), val))

        # 繪圖設定
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=0.8),
            mpf.make_addplot(df['10MA'], color='black', width=0.8),
            mpf.make_addplot(df['20MA'], color='purple', width=0.8)
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(12, 7), volume=True)
        if len(zigzag_points) > 1:
            x, y = zip(*zigzag_points)
            axlist[0].plot(x, y, color='#2196F3', alpha=0.7, linewidth=1.5, zorder=3)
        st.pyplot(fig)
    else:
        st.error(f"找不到 {stock_code} 的數據，可能該股票已下市或資料暫缺。")
