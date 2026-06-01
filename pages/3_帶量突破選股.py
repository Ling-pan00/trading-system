import pandas as pd
import numpy as np

def detect_breakout(df, N=20):
    """
    df: 需要包含 'Close', 'High', 'Low', 'Volume' 的 DataFrame
    N: 箱型區間天數 (預設 20)
    """
    # 1. 計算 N 天內的最高價（箱頂）與最低價（箱底）
    # 使用 shift(1) 是為了確保我們是用「過去」的資料來判斷「今天」是否突破
    df['Box_High'] = df['High'].rolling(window=N).max().shift(1)
    df['Box_Low'] = df['Low'].rolling(window=N).min().shift(1)
    
    # 2. 計算成交量平均值 (用來過濾爆量)
    df['Vol_MA'] = df['Volume'].rolling(window=N).mean()
    
    # 3. 設定買進訊號條件
    # 條件A: 當天收盤價 > 箱頂
    # 條件B: 當天成交量 > 過去 N 天平均成交量的 1.5 倍 (過濾雜訊)
    df['Buy_Signal'] = (df['Close'] > df['Box_High']) & (df['Volume'] > df['Vol_MA'] * 1.5)
    
    return df

# --- 使用教學 ---
# 假設您已經讀取了股價資料到 df
# df = pd.read_csv('your_stock_data.csv') 
# result = detect_breakout(df, N=20)

# 查看所有買點
# buy_points = result[result['Buy_Signal'] == True]
# print(buy_points)
