import streamlit as st
import pandas as pd
import requests
import time
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ==========================================================
# 1. 您的篩選策略 (完全不動，確保邏輯正確)
# ==========================================================
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
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    if "證券代號" in df.columns: df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

def run_strategy():
    df = load(30)
    if df.empty: return pd.DataFrame()
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        # 這是您的篩選邏輯
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock})
    return pd.DataFrame(result)

# ==========================================================
# 2. 獨立繪圖區 (物理隔離，確保型態正確)
# ==========================================================
def draw_chart(stock_id):
    try:
        # 強制補上後綴：上市加.TW，上櫃加.TWO
        # 這是 yfinance 抓不到資料的主因
        sid = str(stock_id).strip()
        ticker = f"{sid}.TW" if int(sid) < 2000 else f"{sid}.TWO"
        
        # 抓取資料
        df = yf.download(ticker, period="3mo", progress=False)
        
        if df.empty:
            st.error(f"⚠️ 無法取得 {ticker} 資料，請確認代號正確。")
            return

        # --- 強制型態清洗：這行是解決 "must be ALL float or int" 的關鍵 ---
        # 將所有非數值資料轉為 NaN，並刪除空值，確保丟給 mpf 的資料是純數字
        df = df.apply(pd.to_numeric, errors='coerce').dropna()
        
        # 繪圖 (只用最單純的蠟燭圖，避免計算衝突)
        fig, ax = mpf.plot(df, type='candle', volume=True, returnfig=True, figsize=(10, 6))
        st.pyplot(fig)
        plt.close(fig)
        
    except Exception as e:
        st.error(f"繪圖發生錯誤: {e}")

# ==========================================================
# 3. 整合執行區
# ==========================================================
st.title("投信鎖碼股 V9.2")

if st.button("開始 V9.2"):
    out = run_strategy()
    if not out.empty:
        st.dataframe(out)
        # 選單只傳代號，徹底隔絕資料污染
        sel = st.selectbox("選擇股票看圖:", out['股票'].unique())
        if sel:
            draw_chart(sel)
    else:
        st.warning("目前無符合篩選標的。")
