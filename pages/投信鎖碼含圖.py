import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# --- 頁面配置 ---
st.set_page_config(page_title="投信鎖碼 V9.2 完整版", layout="wide")
st.title("投信鎖碼 V9.2（自動代號偵測 + K線圖）")

# --- 初始化狀態 ---
if 'final_out' not in st.session_state:
    st.session_state.final_out = pd.DataFrame()

# --- 數據抓取函數 ---
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

# --- 繪圖函數 (自動判斷 .TW / .TWO) ---
def plot_stock(ticker):
    ticker_str = str(ticker).strip()
    # 先試下載 .TW，若無資料則下載 .TWO
    df = yf.download(f"{ticker_str}.TW", period="3mo", progress=False)
    if df.empty or len(df) < 5:
        df = yf.download(f"{ticker_str}.TWO", period="3mo", progress=False)
    
    if df.empty: 
        st.warning(f"找不到 {ticker} 的 K 線資料")
        return
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    fig, ax = mpf.plot(df, type='candle', style='yahoo', returnfig=True, figsize=(10, 5))
    st.pyplot(fig)
    plt.close(fig)

# --- 選股邏輯 ---
if st.button("開始 V9.2 選股"):
    with st.spinner("掃描市場中..."):
        df = load(30)
        if not df.empty:
            stock_col = find(df, ["證券代號"])
            buy_col = find(df, ["買賣超"])
            df[buy_col] = pd.to_numeric(df[buy_col].str.replace(",", ""), errors="coerce").fillna(0)
            
            result = []
            for stock, g in df.groupby(stock_col):
                try:
                    g = g.sort_values("date")
                    series = g[buy_col].values
                    if len(series) < 10: continue
                    last3, last10 = series[-3:], series[-10:]
                    last3_sum, last10_sum = last3.sum(), last10.sum()
                    
                    if (last3 < 0).sum() >= 2 or last10_sum <= 0 or abs(last10_sum) < 20: continue
                    
                    result.append({
                        "股票": stock,
                        "強度": round(last3_sum / (abs(last10_sum) + 1), 4),
                        "穩定度": round(last10_sum / (abs(last3_sum) + 1), 4),
                        "近3日買超": int(last3_sum),
                        "近10日買超": int(last10_sum)
                    })
                except: continue
            
            st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
            st.rerun()

# --- 結果呈現 ---
if not st.session_state.final_out.empty:
    st.success(f"篩選完成，共 {len(st.session_state.final_out)} 檔")
    df_show = st.session_state.final_out
    selected_stock = st.selectbox("選擇股票查看 K 線圖:", df_show["股票"].tolist())
    
    if selected_stock:
        plot_stock(selected_stock)
        
    st.dataframe(df_show, use_container_width=True)
