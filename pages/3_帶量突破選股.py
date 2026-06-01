import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ... (前面的設定與股票池維持不變) ...

# 核心運算邏輯修改部分：
with st.spinner("🚀 正在運算帶量突破與風險參數..."):
    df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
    
    for idx, s_id in enumerate(total_pool):
        # ... (下載與基本資料篩選邏輯) ...
        
        # 1. 計算 ATR (用來衡量波動，作為止損依據)
        df['TR'] = abs(df['High'] - df['Low'])
        df['ATR'] = df['TR'].rolling(window=10).mean()
        
        last_close = df['Close'].iloc[-1]
        high_20 = df['Close'].iloc[-21:-1].max()
        vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
        current_vol = df['Volume'].iloc[-1]
        current_atr = df['ATR'].iloc[-1]
        
        # 2. 策略：突破 + 帶量
        if last_close > high_20 and current_vol > (vol_avg_20 * 2):
            # 進場與風險計算
            entry_price = round(float(last_close), 2)
            # 止損設定：收盤價減去 1.5 倍的 ATR
            stop_loss = round(entry_price - (current_atr * 1.5), 2)
            
            results.append({
                "代碼": s_id, 
                "進場建議": entry_price, 
                "止損價": stop_loss,
                "波動度(ATR)": round(current_atr, 2)
            })

# ... (後續顯示表格程式碼) ...
