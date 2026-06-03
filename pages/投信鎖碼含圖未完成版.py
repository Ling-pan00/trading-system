import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import requests
from datetime import datetime, timedelta
import time

# --- 這是您原本的原始輔助函數 (完全沒變) ---
def get_zigzag_points(df):
    points = []
    if 'Close' not in df.columns: return points
    data = df['Close'].values
    for i in range(1, len(data) - 1):
        if data[i] > data[i-1] and data[i] > data[i+1]:
            points.append((df.index[i], data[i], 'H'))
        elif data[i] < data[i-1] and data[i] < data[i+1]:
            points.append((df.index[i], data[i], 'L'))
    return points

def get_day(date):
    url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={date}&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("stat") != "OK": return None
        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except: return None

def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        df = get_day(d)
        if df is not None and not df.empty: all_df.append(df)
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# --- 介面 ---
st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（原始策略穩定版）")

# 初始化 session
if 'pools' not in st.session_state: st.session_state['pools'] = {}

if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        
        # --- 原始篩選邏輯：完全恢復 ---
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({
            "代號": stock, "股票": stock, "ticker": f"{stock}.TW",
            "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)
        })
    
    st.session_state['out'] = pd.DataFrame(result)
    st.success(f"完成：{len(result)} 檔")
    st.dataframe(st.session_state['out'])

# --- 僅修補圖表區 ---
st.write("---")
st.subheader("🎯 轉折監測器")
if 'out' in st.session_state and not st.session_state['out'].empty:
    pool_all = st.session_state['out']
    sel = st.selectbox("分析個股：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    # 使用 try-except 保護，確保 yfinance 錯誤不會導致當機
    try:
        df_k = yf.download(ticker, period="3mo", progress=False)
        if not df_k.empty:
            if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
            df_k['5MA'] = df_k['Close'].rolling(5).mean()
            df_k['10MA'] = df_k['Close'].rolling(10).mean()
            df_k['20MA'] = df_k['Close'].rolling(20).mean()
            
            # 繪圖 (MPF)
            fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                                   addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
            st.pyplot(fig)
        else:
            st.warning("查無個股資料，請確認代號是否為上市普通股。")
    except Exception as e:
        st.error(f"圖表讀取失敗，原因: {e}")
