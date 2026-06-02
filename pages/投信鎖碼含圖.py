import streamlit as st
import pandas as pd
import requests
import time
import yfinance as yf
import mplfinance as mpf
from datetime import datetime, timedelta

st.set_page_config(page_title="投信鎖碼股穩定版", layout="wide")
st.title("投信鎖碼股 (最終穩定整合版)")

# --- 1. 資料抓取模組 (您的核心) ---
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
        time.sleep(0.05)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 2. 獨立且安全的繪圖模組 ---
def draw_safe_chart(ticker_code):
    try:
        ticker = f"{ticker_code}.TW" if int(ticker_code) < 2000 else f"{ticker_code}.TWO"
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty: 
            st.warning(f"⚠️ 無法取得 {ticker} 數據")
            return
        # 設定轉折 H/B 點計算
        df['h'] = df['High'][(df['High'] > df['High'].shift(1)) & (df['High'] > df['High'].shift(-1))]
        df['l'] = df['Low'][(df['Low'] < df['Low'].shift(1)) & (df['Low'] < df['Low'].shift(-1))]
        ap = [mpf.make_addplot(df['h'], type='scatter', markersize=80, marker='v', color='red'),
              mpf.make_addplot(df['l'], type='scatter', markersize=80, marker='^', color='green')]
        fig, _ = mpf.plot(df, type='candle', volume=True, addplot=ap, mav=(5,10,20), returnfig=True, figsize=(10,6))
        st.pyplot(fig)
    except Exception as e:
        st.error(f"圖表繪製發生異常 (不影響上方篩選): {e}")

# --- 3. 主程式區 (加入防錯邏輯) ---
if st.button("開始執行篩選"):
    df = load(30)
    if df.empty: st.error("沒抓到資料"); st.stop()
    
    # 【關鍵修復】自動搜尋包含「買賣超」的欄位名稱，不再硬寫
    buy_cols = [c for c in df.columns if "買賣超" in str(c)]
    stock_cols = [c for c in df.columns if "證券代號" in str(c)]
    
    if not buy_cols or not stock_cols:
        st.error(f"找不到必要欄位！目前的欄位名稱有: {df.columns.tolist()}")
        st.stop()
        
    b_col, s_col = buy_cols[0], stock_cols[0]
    df[b_col] = pd.to_numeric(df[b_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(s_col):
        series = g.sort_values("date")[b_col].values
        if len(series) < 10 or (series[-3:] < 0).sum() >= 2 or series[-10:].sum() <= 0: continue
        result.append({"股票": stock, "強度": round(series[-3:].sum() / (abs(series[-10:].sum()) + 1), 4)})
    
    out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.dataframe(out)
    
    # 繪圖區獨立於篩選區下方
    sel = st.selectbox("選擇股票查看專業圖:", out["股票"].unique())
    if sel: draw_safe_chart(sel)
