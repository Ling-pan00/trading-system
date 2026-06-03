import yfinance as yf
import pandas as pd
from scipy.signal import argrelextrema
import numpy as np

def find_w_bottom(ticker, period="120d"):
    # 1. 下載資料
    df = yf.download(ticker, period=period)
    if len(df) < 60: return False
    
    # 2. 尋找局部最低點 (比較前後 5 天的極小值)
    df['min'] = df.iloc[argrelextrema(df.Close.values, np.less_equal, order=5)[0]]['Close']
    min_points = df[df['min'].notnull()]
    
    # 3. 判斷是否滿足 W 底條件
    if len(min_points) >= 2:
        # 取最後兩個低點
        last_two = min_points.tail(2)
        l1, l2 = last_two.iloc[0]['min'], last_two.iloc[1]['min']
        
        # 條件：兩個低點價差在 5% 以內
        if abs(l1 - l2) / l1 < 0.05:
            return True
    return False

# 測試：以台積電為例
print(f"台積電是否出現W底: {find_w_bottom('2330.TW')}")
