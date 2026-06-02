import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# 設定頁面為寬版
st.set_page_config(page_title="投信鎖碼 V9.2 實戰版", layout="wide")
st.title("投信鎖碼 V9.2（平衡鎖碼 + 技術轉折版）")

# 初始化 Session State 以保存篩選結果
if 'final_out' not in st.session_state:
    st.session_state.final_out = pd.DataFrame()

# --- 1. 資料載入與原始 V9.2 邏輯 ---
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

# --- 2. 專業繪圖函數 (MA數值、趨勢、轉折標記) ---
def plot_technical_chart(ticker):
    ticker_str = str(ticker).strip()
    df = pd.DataFrame()
    for s in ['.TW', '.TWO']:
        raw = yf.download(f"{ticker_str}{s}", period="3mo", progress=False)
        if not raw.empty and len(raw) > 20: 
            df = raw
            break
    
    if df.empty:
        st.warning(f"查無 {ticker} 股價數據")
        return

    # 計算均線
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA10'] = df['Close'].rolling(10).mean()
    df['MA20'] = df['Close'].rolling(20).mean()

    # 顯示均線數值與趨勢
    cols = st.columns(3)
    for i, ma in enumerate(['MA5', 'MA10', 'MA20']):
        val = df[ma].iloc[-1]
        prev = df[ma].iloc[-2]
        trend = "▲" if val > prev else "▼"
        cols[i].metric(ma, f"{val:.2f}", trend)

    # 轉折偵測 (H=高, B=低)
    df['H'] = (df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))
    df['B'] = (df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))

    # 繪圖
    apds = [
        mpf.make_addplot(df[['MA5', 'MA10', 'MA20']]),
        mpf.make_addplot(df['High'][df['H']], type='scatter', markersize=100, marker='v', color='red'),
        mpf.make_addplot(df['Low'][df['B']], type='scatter', markersize=100, marker='^', color='green')
    ]
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, volume=True, returnfig=True, figsize=(10, 5))
    st.pyplot(fig)
    plt.close(fig)

# --- 3. 選股按鈕 (完整重現 V9.2 規則) ---
if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        # 【你的原始篩選條件】
        last3, last10 = s[-3:], s[-10:]
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({
            "股票": stock, 
            "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4),
            "穩定度": round(last10.sum() / (abs(last3.sum()) + 1), 4)
        })
    
    st.session_state.final_out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.rerun()

# --- 4. 顯示結果 ---
if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    st.success(f"篩選出 {len(st.session_state.final_out)} 檔")
    df_show = st.session_state.final_out
    selected = st.selectbox("選擇股票:", df_show["股票"].tolist())
    plot_technical_chart(selected)
    st.dataframe(df_show, use_container_width=True)
