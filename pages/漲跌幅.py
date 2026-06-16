import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import requests
import io

st.set_page_config(layout="wide")
st.title("📈 完整版：漲跌幅排行與轉折標註系統")

# 1. 爬蟲函數 (使用 BeautifulSoup 處理 Yahoo 排行)
@st.cache_data(ttl=3600)
def get_yahoo_ranking(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        # 這裡改用 pd.read_html 處理，若遇到格式問題建議檢查網頁路徑
        dfs = pd.read_html(io.StringIO(res.text))
        return dfs[0] if dfs else None
    except Exception as e:
        return None

# 2. 初始化排行榜 (抓取漲幅與跌幅)
if 'stock_list' not in st.session_state:
    up = get_yahoo_ranking("https://tw.stock.yahoo.com/rank/change-up/")
    down = get_yahoo_ranking("https://tw.stock.yahoo.com/rank/change-down/")
    
    combined = []
    if up is not None: combined += [f"{s.split('.')[0]}.TW (漲幅)" for s in up['代號'].astype(str)]
    if down is not None: combined += [f"{s.split('.')[0]}.TW (跌幅)" for s in down['代號'].astype(str)]
    st.session_state.stock_list = combined

selected = st.selectbox("請選擇排行中的個股:", st.session_state.stock_list)
stock_code = selected.split(' ')[0]

# 3. 資料下載與計算轉折邏輯
@st.cache_data
def get_data(ticker):
    df = yf.download(ticker, period="6mo", auto_adjust=True)
    if df.empty: return None
    df['5MA'] = df['Close'].rolling(5).mean()
    # 轉折判斷邏輯
    df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
    df['Signal'] = df['State'].diff()
    return df.dropna()

df = get_data(stock_code)

if df is not None:
    # 準備標註轉折點
    buy_signals = df[df['Signal'] == 2]
    sell_signals = df[df['Signal'] == -2]
    
    ap = [
        mpf.make_addplot(df['5MA'], color='orange'),
        mpf.make_addplot(buy_signals['Close'], type='scatter', markersize=100, marker='^', color='red'),
        mpf.make_addplot(sell_signals['Close'], type='scatter', markersize=100, marker='v', color='green')
    ]
    
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=ap, returnfig=True)
    st.pyplot(fig)
else:
    st.error("該股票暫無資料")
