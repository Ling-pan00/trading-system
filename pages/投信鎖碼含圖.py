import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time
# 繪圖模組需要的套件
import yfinance as yf
import matplotlib.pyplot as plt
import mplfinance as mpf

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（平衡實戰版）")

# --- 您的原始核心邏輯 (完全原樣保留) ---
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

# --- 獨立掛載的繪圖函數 (完全隔離) ---
def draw_chart(stock_code):
    try:
        # 自動識別上市(.TW)或上櫃(.TWO)
        ticker = f"{stock_code}.TW" if int(stock_code) < 2000 else f"{stock_code}.TWO"
        df = yf.download(ticker, period="3mo", progress=False)
        if df.empty:
            st.warning(f"⚠️ 找不到 {stock_code} 的市場數據")
            return
        
        # 簡單範例繪圖
        fig, ax = plt.subplots()
        ax.plot(df['Close'], label='Close Price')
        ax.set_title(f"{stock_code} Price Chart")
        st.pyplot(fig)
    except Exception as e:
        st.error(f"繪圖模組錯誤: {e}")

# --- 主程式區 ---
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty: st.error("沒有抓到資料"); st.stop()

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])

    if stock_col is None or buy_col is None:
        st.error("欄位解析失敗"); st.stop()

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
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

    out = pd.DataFrame(result)
    if out.empty: st.warning("目前市場沒有明顯投信鎖碼"); st.stop()
    out = out.sort_values("強度", ascending=False)
    
    # 顯示表格
    st.success(f"完成：{len(out)} 檔")
    st.dataframe(out)

    # 在表格下方掛載選擇器
    sel = st.selectbox("選擇股票查看轉折圖:", out["股票"].unique())
    if sel: draw_chart(str(sel))
