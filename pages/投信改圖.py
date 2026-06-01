import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt

# ==========================================
# 1. 完整 565 檔股池定義 (請確保清單完整)
# ==========================================
def get_industry_stock_pool():
    # 這裡放入您的完整 565 檔清單
    return [
        "1503.TW", "1504.TW", "1513.TW", "1514.TW", "1519.TW", "1521.TW", "1522.TW", "1524.TW", "1525.TW", "1526.TW",
        "1527.TW", "1528.TW", "1529.TW", "1530.TW", "1531.TW", "1532.TW", "1533.TW", "1535.TW", "1536.TW", "1537.TW",
        "1538.TW", "1539.TW", "1540.TW", "1541.TW", "1560.TW", "1582.TW", "1583.TWO", "1584.TWO", "1586.TWO", "1587.TWO",
        "1591.TWO", "1593.TWO", "1597.TWO", "1599.TWO", "1605.TW", "1608.TW", "1704.TW", "1708.TW", "1710.TW", "1711.TW",
        "1712.TW", "1713.TW", "1714.TW", "1717.TW", "1718.TW", "1720.TW", "1721.TW", "1722.TW", "1723.TW", "1726.TW",
        "1727.TW", "1730.TW", "1731.TW", "1732.TW", "1733.TW", "1734.TW", "1735.TW", "1736.TW", "1742.TWO", "1750.TWO",
        "2302.TW", "2303.TW", "2329.TW", "2330.TW", "2337.TW", "2338.TW", "2344.TW", "2351.TW", "2363.TW", "2369.TW",
        "2379.TW", "2388.TW", "2408.TW", "2436.TW", "2441.TW", "2449.TW", "2454.TW", "2458.TW", "2481.TW", "3006.TW",
        "3016.TW", "3034.TW", "3035.TW", "3041.TW", "3054.TW", "3094.TWO", "3105.TWO", "3131.TWO", "3141.TWO", "3169.TWO",
        "3189.TW", "3227.TWO", "3228.TWO", "3260.TWO", "3264.TWO", "3265.TWO", "3289.TWO", "3374.TWO", "3413.TW", "3438.TWO",
        "3443.TW", "3527.TWO", "3529.TWO", "3532.TW", "3545.TW", "3556.TWO", "3567.TWO", "3583.TW", "3587.TWO", "3588.TWO",
        "3592.TWO", "3653.TW", "3661.TW", "3675.TWO", "3680.TWO", "3686.TW", "3707.TWO", "3711.TW", "4919.TW", "4952.TW",
        "4961.TW", "4966.TWO", "4967.TW", "4968.TW", "4976.TW", "5269.TW", "5274.TWO", "5285.TW", "5289.TWO", "5305.TW",
        "5347.TWO", "5351.TWO", "5425.TWO", "5471.TWO", "5483.TWO", "6104.TWO", "6125.TWO", "6129.TWO", "6138.TWO", "6147.TWO",
        "6182.TWO", "6202.TW", "6224.TW", "6239.TW", "6243.TW", "6257.TW", "6271.TW", "6287.TWO", "6411.TWO", "6415.TW",
        "6435.TWO", "6451.TW", "6462.TWO", "6488.TWO", "6494.TWO", "6510.TWO", "6526.TW", "6531.TW", "6533.TW", "6548.TWO",
        "6568.TWO", "6573.TWO", "6679.TWO", "6684.TWO", "6719.TW", "6732.TWO", "6756.TW", "6770.TW", "6789.TW", "6806.TW",
        "6834.TWO", "8016.TW", "8028.TWO", "8054.TWO", "8081.TWO", "8110.TW", "8131.TW", "8150.TW", "8261.TW", "8271.TW"
        # ... (請確保此處補齊所有 565 檔代號)
    ]

# ==========================================
# 2. 核心邏輯與完整執行
# ==========================================
st.set_page_config(layout="wide")
if 'cache' not in st.session_state: st.session_state.cache = {}

pool = get_industry_stock_pool()

if st.button(f"執行掃描 ({len(pool)} 檔)"):
    df_raw = yf.download(pool, period="6mo", auto_adjust=True, group_by='ticker', progress=False)
    results = []
    for s in pool:
        df = df_raw[s] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
        if len(df) < 65: continue
        # 您的篩選邏輯
        if df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1] and \
           df['Close'].iloc[-1] > df['Close'].rolling(60).mean().iloc[-1] and \
           (df['Volume'].iloc[-1] / 50000000) * 100 < 5.0:
            results.append(s)
            st.session_state.cache[s] = df
    st.session_state.results = results

if 'results' in st.session_state:
    pick = st.selectbox("選擇個股:", st.session_state.results)
    df = st.session_state.cache[pick].tail(60).copy()
    
    # 計算 MA 與轉折
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['State'] = np.where(df['Close'] > df['MA5'], 1, -1)
    df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()
    
    pts = []
    for gid, g in df.groupby('State_Group'):
        if gid <= 2: continue
        idx = g['High'].idxmax() if g['State'].iloc[0] == 1 else g['Low'].idxmin()
        pts.append((df.index.get_loc(idx), df.loc[idx, 'High'] if g['State'].iloc[0] == 1 else df.loc[idx, 'Low'], "H" if g['State'].iloc[0] == 1 else "B"))
    
    # 精準重現樣式
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', y_on_right=True)
    
    ap = [
        mpf.make_addplot(df['MA5'], color='orange', width=1.0),
        mpf.make_addplot(df['MA20'], color='purple', width=1.0)
    ]
    
    fig, ax = mpf.plot(df, type='candle', style=s, addplot=ap, returnfig=True, volume=True, panel_ratios=(4,1), figsize=(12, 7))
    
    # 繪製黑色轉折線
    if pts:
        x, y, labels = zip(*pts)
        ax[0].plot(x, y, color='black', alpha=0.6, linewidth=1.5)
        for px, py, label in pts:
            ax[0].annotate(label, (px, py), color='white', ha='center', va='center', 
                           bbox=dict(boxstyle='circle', fc='red' if label=='H' else 'green', ec='none'))
    
    st.pyplot(fig)
