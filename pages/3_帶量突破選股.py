import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf

st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
st.title("📊 565 檔強勢帶量突破選股系統")

# 強制清理資料函數
def clean_yf_data(df):
    # 處理 MultiIndex 欄位
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # 統一轉為小寫
    df.columns = [c.lower() for c in df.columns]
    # 確保含有必要欄位
    required = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required):
        return None
    return df.dropna()

def draw_zigzag_chart(df, ticker):
    df = clean_yf_data(df)
    if df is None:
        st.error("無法解析數據格式")
        return

    # 計算轉折點
    df['5ma'] = df['close'].rolling(5).mean()
    df['state'] = np.where(df['close'] > df['5ma'], 1, -1)
    df['state_group'] = (df['state'] != df['state'].shift()).cumsum()
    
    h_pts, b_pts = [], []
    for _, g in df.groupby('state_group'):
        if len(g) < 2: continue
        if g['state'].iloc[0] == 1:
            idx = g['high'].idxmax()
            h_pts.append((df.index.get_loc(idx), g.loc[idx, 'high']))
        else:
            idx = g['low'].idxmin()
            b_pts.append((df.index.get_loc(idx), g.loc[idx, 'low']))
            
    # 繪圖參數設定
    s = mpf.make_mpf_style(base_mpf_style='charles', gridstyle='--')
    fig, axlist = mpf.plot(df, type='candle', style=s, returnfig=True, figsize=(10, 6), title=f"{ticker} 轉折走勢")
    
    # 繪製轉折線
    all_pts = sorted(h_pts + b_pts)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linewidth=1.5)
    
    # 標記高低點
    for x, y in h_pts: axlist[0].text(x, y, 'H', color='red', weight='bold', ha='center', bbox=dict(facecolor='yellow', boxstyle='circle'))
    for x, y in b_pts: axlist[0].text(x, y, 'L', color='blue', weight='bold', ha='center', bbox=dict(facecolor='cyan', boxstyle='circle'))
    st.pyplot(fig)

# 主程式邏輯
if st.button("🚀 啟動全量掃描"):
    # 這裡請確保放入完整的 565 檔清單
    pool = ["2330.TW", "2454.TW", "3008.TW"] # 請替換為您的清單
    results = []
    for s in pool:
        df = yf.download(s, period="2mo", progress=False)
        df = clean_yf_data(df)
        if df is not None and len(df) > 20:
            if df['close'].iloc[-1] > df['close'].iloc[-21:-1].max() and \
               df['volume'].iloc[-1] > (df['volume'].iloc[-21:-1].mean() * 2):
                results.append(s)
    st.session_state['res'] = results

if 'res' in st.session_state and st.session_state['res']:
    sel = st.selectbox("選擇標的", st.session_state['res'])
    if st.button("檢視轉折圖"):
        df = yf.download(sel, period="6mo", progress=False)
        draw_zigzag_chart(df, sel)
