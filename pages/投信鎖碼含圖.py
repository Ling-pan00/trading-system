import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V9.2 實戰版", layout="wide")
st.title("投信鎖碼 V9.2（技術轉折實戰版）")

# --- 數據抓取 ---
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

# --- 繪圖邏輯：MA 線 + 處理空值避免 ValueError ---
def plot_technical_chart(ticker):
    ticker_str = str(ticker).strip()
    df = pd.DataFrame()
    for suffix in ['.TW', '.TWO']:
        raw_df = yf.download(f"{ticker_str}{suffix}", period="3mo", progress=False)
        if not raw_df.empty and len(raw_df) > 10:
            df = raw_df
            break
    
    if df.empty:
        st.warning(f"找不到 {ticker} 的資料")
        return

    # 清洗：處理 MultiIndex 與缺失值
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # 計算 MA
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    apds = [
        mpf.make_addplot(df['MA5'], color='orange', width=1),
        mpf.make_addplot(df['MA10'], color='blue', width=1),
        mpf.make_addplot(df['MA20'], color='purple', width=1)
    ]
    
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, 
                       volume=True, returnfig=True, figsize=(10, 6))
    st.pyplot(fig)
    plt.close(fig)

# --- V9.2 選股核心邏輯 ---
if st.button("開始 V9.2 選股"):
    df = load(30)
    if not df.empty:
        stock_col = find(df, ["證券代號"])
        buy_col = find(df, ["買賣超"])
        df[buy_col] = pd.to_numeric(df[buy_col].str.replace(",", ""), errors="coerce").fillna(0)
        
        result = []
        for stock, g in df.groupby(stock_col):
            g = g.sort_values("date")
            s = g[buy_col].values
            if len(s) < 10: continue
            
            # 您原有的核心策略
            if (s[-3:] < 0).sum() >= 2 or s[-10:].sum() <= 0 or abs(s[-10:].sum()) < 20: continue
            
            result.append({
                "股票": stock,
                "強度": round(s[-3:].sum() / (abs(s[-10:].sum()) + 1), 4),
                "穩定度": round(s[-10:].sum() / (abs(s[-3:].sum()) + 1), 4)
            })
        
        st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
        st.rerun()

# --- 結果顯示 ---
if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    selected = st.selectbox("選擇股票查看技術線圖:", st.session_state.final_out["股票"].tolist())
    plot_technical_chart(selected)
    st.dataframe(st.session_state.final_out, use_container_width=True)
