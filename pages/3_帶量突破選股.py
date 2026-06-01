import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf

# 頁面基本設定
st.set_page_config(page_title="強勢股選股", layout="wide")
st.title("📊 565 檔強勢帶量突破系統 (白底版)")

# 股票清單 (結構化處理，減少語法錯誤風險)
def get_pool():
    return ["1503.TW", "1504.TW", "1513.TW", "1514.TW", "1519.TW", "1521.TW", "1522.TW", "1524.TW", "1525.TW", "1526.TW",
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
            "6834.TWO", "8016.TW", "8028.TWO", "8054.TWO", "8081.TWO", "8110.TW", "8131.TW", "8150.TW", "8261.TW", "8271.TW"]

# 繪圖函數
def plot_chart(df):
    # 建立樣式：白底
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--', facecolor='white')
    
    # 繪圖
    fig, ax = mpf.plot(df, type='candle', style=s, figsize=(10, 6), volume=True, returnfig=True)
    st.pyplot(fig)
    plt.close(fig)

# 掃描邏輯
if st.button("🚀 執行篩選"):
    pool = get_pool()
    data = yf.download(pool, period="3mo", group_by='ticker', auto_adjust=True, progress=False)
    
    for t in pool:
        try:
            df = data[t].copy() if len(pool) > 1 else data.copy()
            df.columns = [c.capitalize() for c in df.columns]
            
            # 判斷條件：收盤 > 20日最高價 且 成交量 > 20日均量 1.2倍
            if df['Close'].iloc[-1] > df['High'].iloc[-21:-1].max() and \
               df['Volume'].iloc[-1] > df['Volume'].iloc[-21:-1].mean() * 1.2:
                st.subheader(f"✅ {t}")
                plot_chart(df)
        except:
            continue
