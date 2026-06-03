import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="5MA 轉折波段系統", layout="wide")
st.title("📈 5MA 轉折波段自動標註系統")

stock_code = st.text_input("請輸入台灣股票代號:", "4768")
end_date = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
start_date = (datetime.today() - timedelta(days=180)).strftime('%Y-%m-%d')

@st.cache_data
def load_data(ticker, start, end):
    return yf.download(ticker, start=start, end=end)

if stock_code:
    df = None
    for ticker in [f"{stock_code}.TW", f"{stock_code}.TWO"]:
        temp = load_data(ticker, start_date, end_date)
        if not temp.empty:
            df = temp
            break
    
    if df is not None:
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['5MA'] = df['Close'].rolling(5).mean()
        df = df.dropna().copy()

        # 核心邏輯：強制包含當日找極值
        df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)
        df['Label'] = None
        
        # 尋找所有轉折點 (State 改變的瞬間)
        change_indices = df.index[df['State'] != df['State'].shift()].tolist()
        # 加入最後一行作為截止點，確保包含今日
        if df.index[-1] not in change_indices:
            change_indices.append(df.index[-1])
        
        zigzag_points = []
        for i in range(len(change_indices) - 1):
            start_i = change_indices[i]
            end_i = change_indices[i+1]
            # 獲取區間數據 (包含 start_i 到 end_i)
            subset = df.loc[start_i:end_i]
            
            # 如果是在 5MA 之上 (1) 找高點；之下 (-1) 找低點
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
        fig, axlist = mpf.plot(df, type='candle', style=s, addplot=[mpf.make_addplot(df['5MA'])], 
                               returnfig=True, figsize=(12, 7), volume=True)
        
        main_ax = axlist[0]
        if len(zigzag_points) > 1:
            x, y = zip(*zigzag_points)
            main_ax.plot(x, y, color='black', alpha=0.5, linewidth=1.5)
            
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            val = row['High'] if row['Label'] == "H" else row['Low']
            color = "red" if row['Label'] == "H" else "green"
            main_ax.annotate(row['Label'], xy=(x, val), bbox=dict(boxstyle="circle", fc=color, ec="none"))
            main_ax.annotate(f"{val:.2f}", xy=(x, val), xytext=(0, 30 if row['Label']=="H" else -30), 
                             textcoords='offset points', ha='center', fontsize=9)
        st.pyplot(fig)
