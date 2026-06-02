import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
# 將繪圖相關庫全部移至頂端，確保不會在執行中途出現 NameError
import yfinance as yf
import matplotlib.pyplot as plt

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（穩定實戰版）")

# --- 您的原始核心邏輯 (一字未改) ---
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
    if "證券代號" in df.columns:
        df = df.sort_values(["證券代號", "date"])
    return df

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

# --- 獨立且防錯的繪圖模組 ---
def draw_chart_safe(ticker_code):
    try:
        # 自動處理上市/上櫃代號後綴
        code = str(ticker_code).strip()
        ticker = f"{code}.TW" if int(code) < 2000 else f"{code}.TWO"
        
        st.write(f"正在嘗試獲取 {ticker} 市場數據...")
        df = yf.download(ticker, period="3mo", progress=False)
        
        if df.empty:
            st.warning(f"⚠️ 找不到 {ticker} 的市場數據，請確認該代號。")
            return
            
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df['Close'], label='Close Price')
        ax.set_title(f"{ticker} Price")
        st.pyplot(fig)
    except Exception as e:
        st.error(f"繪圖模組執行異常 (已攔截): {e}")

# --- 主程式區 (完全保護您的核心篩選) ---
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty: st.error("沒有抓到資料"); st.stop()

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    if stock_col is None or buy_col is None: st.error("欄位解析失敗"); st.stop()

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    result = []

    for stock, g in df.groupby(stock_col):
        try:
            g = g.sort_values("date")
            series = g[buy_col].values
            if len(series) < 10: continue
            last3_sum, last10_sum = series[-3:].sum(), series[-10:].sum()
            if (series[-3:] < 0).sum() >= 2 or last10_sum <= 0 or abs(last10_sum) < 20: continue
            
            result.append({
                "股票": stock,
                "強度": round(last3_sum / (abs(last10_sum) + 1), 4),
                "近10日買超": int(last10_sum)
            })
        except: continue

    out = pd.DataFrame(result)
    st.dataframe(out.sort_values("強度", ascending=False))
    
    # 獨立的選股繪圖框，失敗也不會影響上方表格
    sel = st.selectbox("選擇股票查看轉折圖:", out["股票"].unique())
    if sel: draw_chart_safe(sel)
