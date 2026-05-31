import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np

# 1. 下載資料 (以岱稜 3303.TW 為例)
stock_id = "3303.TW" 
df = yf.download(stock_id, start="2026-01-01", end="2026-05-30")

# 2. 計算 5MA
df['5MA'] = df['Close'].rolling(window=5).mean()
df = df.dropna().copy()

# 3. 定義狀態：1 代表在 5MA 之上，-1 代表在 5MA 之下
df['State'] = np.where(df['Close'] > df['5MA'], 1, -1)

# 4. 找出狀態轉折的起點 (用來切分不固定天數的區間)
# 當 State_Group 改變時，代表進入了新的波段
df['State_Group'] = (df['State'] != df['State'].shift()).cumsum()

# 建立儲存你要的目標線欄位
df['Target_Line'] = np.nan

# 5. 開始動態回溯計算
for i in range(len(df)):
    current_state = df['State'].iloc[i]
    current_group = df['State_Group'].iloc[i]
    
    # 必須要有前期的資料才能往回找「上一個」區間
    if current_group <= 2:
        continue
        
    if current_state == 1:
        # 【條件 1】目前站上 5MA，要找「上一個」頭部區間 (即上一次 State == 1 的群組)
        # 也就是目前群組編號減 2 的那個區間
        target_group_id = current_group - 2
        prev_head_zone = df[df['State_Group'] == target_group_id]
        
        if not prev_head_zone.empty:
            # 找到該頭部區間之內的最低價
            df.loc[df.index[i], 'Target_Line'] = prev_head_zone['Low'].min()
            
    elif current_state == -1:
        # 【條件 2】目前跌破 5MA，要找「上一個」底部區間 (即上一次 State == -1 的群組)
        target_group_id = current_group - 2
        prev_bottom_zone = df[df['State_Group'] == target_group_id]
        
        if not prev_bottom_zone.empty:
            # 找到該底部區間之內的最高價
            df.loc[df.index[i], 'Target_Line'] = prev_bottom_zone['High'].max()

# 6. 畫出 K 線圖與動態標註線
plots = [
    mpf.make_addplot(df['5MA'], color='orange', width=1),
    # 使用 scatter 畫出每日計算出來的對應目標價 (呈現水平線效果)
    mpf.make_addplot(df['Target_Line'], color='blue', type='scatter', markersize=15, marker='_')
]

mpf.plot(df, type='candle', style='charles', addplot=plots, title=f"{stock_id} Dynamic Waves")
