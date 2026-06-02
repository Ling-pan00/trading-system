import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
import requests
import time
from datetime import datetime, timedelta

# --- 1. 投信資料載入 (您的核心) ---
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

# --- 2. 專業轉折繪圖 (含 K 線, MA, H/B 標記) ---
def draw_pro_chart(ticker_code):
    try:
        # 自動識別上市/上櫃
        ticker = f"{ticker_code}.TW" if int(ticker_code) < 2000 else f"{ticker_code}.TWO"
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty: raise ValueError("無數據")

        # 計算轉折點 (H/B 邏輯)
        df['h_point'] = df['High'][(df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))]
        df['l_point'] = df['Low'][(df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))]

        # 設定圖表元素
        addplots = [
            mpf.make_addplot(df['h_point'], type='scatter', markersize=80, marker='v', color='red'),
            mpf.make_addplot(df['l_point'], type='scatter', markersize=80, marker='^', color='green')
        ]
        
        # 繪製
        fig, ax = mpf.plot(df, type='candle', style='charles', volume=True, 
                           addplot=addplots, mav=(5, 10, 20), returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"圖表無法顯示 (代號 {ticker_code}): {e}")

# --- 3. 主程式介面 ---
st.set_page_config(page_title="投信鎖碼股 Pro", layout="wide")
st.title("投信鎖碼股 V9.2 (完整版)")

if st.button("執行篩選"):
    df = load(30)
    if df.empty: st.stop()
    
    # 手動指定欄位，確保不崩潰
    df["買賣超"] = pd.to_numeric(df["買賣超"], errors="coerce").fillna(0)
    result = []
    
    # 篩選邏輯
    for stock, g in df.groupby("證券代號"):
        series = g.sort_values("date")["買賣超"].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock, "強度": round(series[-3:].sum() / (abs(series[-10:].sum()) + 1), 4)})

    out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.dataframe(out)

    # 專業圖表選擇器
    sel = st.selectbox("選擇股票查看專業圖:", out["股票"].unique())
    if sel: draw_pro_chart(sel)
