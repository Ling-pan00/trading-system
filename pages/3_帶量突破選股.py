import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import mplfinance as mpf

st.set_page_config(page_title="強勢帶量突破診斷", layout="wide")
st.title("📊 565 檔強勢帶量突破選股系統")

# 1. 確保資料讀取與結構清洗
def get_clean_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty: return None
        # 若是 MultiIndex 則清理
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [c.lower() for c in df.columns]
        return df.dropna()
    except:
        return None

# 2. 轉折圖繪製 (Zigzag)
def draw_zigzag_chart(df, ticker):
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
            
    fig, axlist = mpf.plot(df, type='candle', style='charles', returnfig=True, figsize=(10, 6), title=f"{ticker} 轉折走勢")
    
    all_pts = sorted(h_pts + b_pts)
    if len(all_pts) > 1:
        x, y = zip(*all_pts)
        axlist[0].plot(x, y, color='gray', linewidth=1.5, zorder=2)
    
    for x, y in h_pts: axlist[0].text(x, y, 'H', color='red', fontweight='bold', ha='center', bbox=dict(facecolor='yellow', boxstyle='circle'))
    for x, y in b_pts: axlist[0].text(x, y, 'L', color='blue', fontweight='bold', ha='center', bbox=dict(facecolor='cyan', boxstyle='circle'))
    st.pyplot(fig)

# 3. 主程式
if st.button("🚀 開始掃描所有標的"):
    # 這裡請放入您的完整 565 檔代碼
    pool = ["2330.TW", "2317.TW", "2454.TW", "3008.TW", "2303.TW", "2308.TW"] 
    results = []
    
    with st.spinner("正在分析市場..."):
        for s in pool:
            df = get_clean_data(s)
            if df is not None and len(df) > 21:
                # 條件：收盤價 > 20日最高價 且 今日成交量 > 20日均量 * 1.5 (調整倍率測試)
                if df['close'].iloc[-1] > df['close'].iloc[-21:-1].max() and \
                   df['volume'].iloc[-1] > (df['volume'].iloc[-21:-1].mean() * 1.5):
                    results.append(s)
    
    if results:
        st.session_state['res'] = results
        st.success(f"篩選出 {len(results)} 檔標的")
    else:
        st.warning("未篩選出股票，建議檢查是否為週末/節假日無交易，或試著放寬成交量倍數條件。")

if 'res' in st.session_state and st.session_state['res']:
    sel = st.selectbox("請選擇要分析的標的", st.session_state['res'])
    if st.button("繪製轉折圖"):
        df = get_clean_data(sel)
        draw_zigzag_chart(df, sel)
