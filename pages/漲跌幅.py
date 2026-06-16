import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import requests
from datetime import datetime, timedelta

# 系統設定
st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統 (含排行榜)")

# 1. 抓取 Yahoo 股市排行榜
@st.cache_data(ttl=3600) # 快取 1 小時
def get_yahoo_ranking(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        dfs = pd.read_html(res.text)
        if len(dfs) > 0:
            df_rank = dfs[0]
            # 假設表格中包含 '代號' 欄位
            return df_rank
        return None
    except Exception as e:
        st.error(f"抓取失敗: {e}")
        return None

# 2. 資料下載函數
@st.cache_data
def load_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end, auto_adjust=True)

# 側邊欄：選擇股票來源
mode = st.sidebar.radio("選擇股票來源", ["手動輸入", "漲幅排行", "跌幅排行"])

stock_code = ""
if mode == "手動輸入":
    stock_code = st.text_input("請輸入台灣股票代號 (例如: 6412):", "6412")
else:
    url = "https://tw.stock.yahoo.com/rank/change-up/" if mode == "漲幅排行" else "https://tw.stock.yahoo.com/rank/change-down/"
    rank_df = get_yahoo_ranking(url)
    if rank_df is not None:
        # 假設 '代號' 是欄位名稱
        stock_list = rank_df['代號'].astype(str).tolist()
        selected = st.selectbox("請從排行榜選擇股票:", stock_list)
        stock_code = selected.split('.')[0] # 提取代號部分
    else:
        st.warning("無法取得排行資料")

# 3. 處理與繪圖
if stock_code:
    end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')
    
    df = None
    for ticker in [f"{stock_code}.TW", f"{stock_code}.TWO"]:
        temp = load_data(ticker, start_date, end_date)
        if not temp.empty:
            df = temp
            break
    
    if df is not None and not df.empty:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 計算均線
        df['5MA'] = df['Close'].rolling(5).mean()
        df['10MA'] = df['Close'].rolling(10).mean()
        df['20MA'] = df['Close'].rolling(20).mean()
        df = df.dropna().copy()

        # 波段邏輯
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

        # 繪圖
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        ap = [
            mpf.make_addplot(df['5MA'], color='orange', width=0.8),
            mpf.make_addplot(df['10MA'], color='black', width=0.8),
            mpf.make_addplot(df['20MA'], color='purple', width=0.8)
        ]
        
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, figsize=(12, 7), volume=True, panel_ratios=(3, 1))
        main_ax = axlist[0]
        
        if len(zigzag_points) > 1:
            x, y = zip(*zigzag_points)
            main_ax.plot(x, y, color='#2196F3', alpha=0.7, linewidth=1.5, zorder=3)
            
        st.pyplot(fig)
    else:
        st.error("查無資料，請確認代號是否正確。")
