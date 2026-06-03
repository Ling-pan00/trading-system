import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock
import requests
from datetime import datetime, timedelta
import time

# --- 原始核心函數 (完全原樣) ---
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

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（平衡實戰版）")

# 解決 session_state 遺失導致圖表出不來的關鍵：初始化並儲存結果
if 'out' not in st.session_state: st.session_state['out'] = pd.DataFrame()
if 'pools' not in st.session_state: st.session_state['pools'] = {"投信": pd.DataFrame()}

# --- 開始按鈕邏輯 ---
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
        
        # --- 原始策略條件 (完全不動) ---
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({
            "股票": stock, "代號": stock, "ticker": f"{stock}.TW",
            "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4),
            "穩定度": round(last10.sum() / (abs(last3.sum()) + 1), 4),
            "近3日買超": int(last3.sum()), "近10日買超": int(last10.sum())
        })
    
    st.session_state['out'] = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.session_state['pools']["投信"] = st.session_state['out']
    st.success(f"完成：{len(st.session_state['out'])} 檔")

# --- 繪圖區 (僅修復連線錯誤) ---
st.write("---")
st.subheader("🎯 轉折監測器")
if not st.session_state['out'].empty:
    pool_all = st.session_state['out']
    sel = st.selectbox("分析個股：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    # 強力修正：確保 yfinance 抓不到資料時，不會當機
    df_k = yf.download(ticker, period="3mo", progress=False)
    if not df_k.empty:
        if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
        df_k['5MA'], df_k['10MA'], df_k['20MA'] = df_k['Close'].rolling(5).mean(), df_k['Close'].rolling(10).mean(), df_k['Close'].rolling(20).mean()
        
        # HTML 板 (原始)
        l, p = df_k.iloc[-1], df_k.iloc[-2]
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
                <span style="color: #FF9800; margin-right: 20px;">5MA: {l['5MA']:.2f} {'▲' if l['5MA'] > p['5MA'] else '▼'}</span>
                <span style="color: #2196F3; margin-right: 20px;">10MA: {l['10MA']:.2f} {'▲' if l['10MA'] > p['10MA'] else '▼'}</span>
                <span style="color: #9C27B0;">20MA: {l['20MA']:.2f} {'▲' if l['20MA'] > p['20MA'] else '▼'}</span>
            </div>
        """, unsafe_allow_html=True)
        
        # 繪圖 (MPF)
        fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                               addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
        ax = axlist[0]
        for idx, val, lbl in get_zigzag_points(df_k):
            if idx in df_k.iloc[-90:].index:
                ax.annotate(lbl, (df_k.index.get_loc(idx), val), ha='center', color='red' if lbl=='H' else 'green', weight='bold', bbox=dict(fc="yellow", alpha=0.5))
        st.pyplot(fig)
