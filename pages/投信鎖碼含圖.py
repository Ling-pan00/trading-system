import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# 設定頁面
st.set_page_config(page_title="投信鎖碼 V9.2 完整實戰版", layout="wide")
st.title("投信鎖碼 V9.2（平衡鎖碼 + 技術轉折版）")

# 初始化 Session State
if 'final_out' not in st.session_state:
    st.session_state.final_out = pd.DataFrame()

# --- 原始 V9.2 抓取與工具函數 ---
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

# --- 技術分析繪圖函數 (MA + 高低轉折點標記) ---
def plot_technical_chart(ticker):
    ticker_str = str(ticker).strip()
    df = pd.DataFrame()
    for suffix in ['.TW', '.TWO']:
        raw_df = yf.download(f"{ticker_str}{suffix}", period="3mo", progress=False)
        if not raw_df.empty and len(raw_df) > 20:
            df = raw_df
            break
    
    if df.empty:
        st.warning(f"找不到 {ticker} 的股價資料")
        return

    # 數據清洗
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # 計算 MA
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # 繪圖參數設定
    apds = [
        mpf.make_addplot(df['MA5'], color='orange', width=1.5, label='5MA'),
        mpf.make_addplot(df['MA10'], color='blue', width=1.5, label='10MA'),
        mpf.make_addplot(df['MA20'], color='purple', width=1.5, label='20MA')
    ]
    
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, 
                       volume=True, returnfig=True, figsize=(12, 6))
    
    st.write(f"### {ticker} 技術分析圖")
    st.pyplot(fig)
    plt.close(fig)

# --- V9.2 選股核心邏輯 ---
if st.button("開始 V9.2"):
    df = load(30)
    if not df.empty:
        stock_col = find(df, ["證券代號"])
        buy_col = find(df, ["買賣超"])
        df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(",", ""), errors="coerce").fillna(0)
        
        result = []
        for stock, g in df.groupby(stock_col):
            g = g.sort_values("date")
            series = g[buy_col].values
            if len(series) < 10: continue
            
            # 您原有的邏輯
            last3, last10 = series[-3:], series[-10:]
            if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
            
            result.append({
                "股票": stock,
                "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4),
                "穩定度": round(last10.sum() / (abs(last3.sum()) + 1), 4)
            })
        
        st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
        st.rerun()

# --- 顯示區 ---
if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    st.success(f"完成篩選，共 {len(st.session_state.final_out)} 檔")
    df_show = st.session_state.final_out
    selected_stock = st.selectbox("選擇股票查看 K 線圖:", df_show["股票"].tolist())
    
    if selected_stock:
        plot_technical_chart(selected_stock)
        
    st.dataframe(df_show, use_container_width=True)
