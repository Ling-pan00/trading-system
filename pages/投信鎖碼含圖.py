import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼", layout="wide")
st.title("📊 投信鎖碼分析 (策略還原版)")

# =========================
# 1. 資料載入區 (完全不動)
# =========================
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

# =========================
# 2. 繪圖區 (獨立模組)
# =========================
def draw_chart(ticker):
    try:
        # 強制補上 .TW 避免找不到資料
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty:
            st.error(f"⚠️ 無法取得 {ticker} 資料")
            return
        
        # 繪圖樣式
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        fig, ax = mpf.plot(df, type='candle', style=s, returnfig=True, figsize=(10, 5))
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error(f"繪圖錯誤: {e}")

# =========================
# 3. 主程式 (完全依照您的原始策略)
# =========================
if st.button("🚀 開始 V9.2 分析"):
    df = load(30)
    if df.empty: st.error("資料載入失敗"); st.stop()

    # 直接使用原始欄位名稱，不再使用自動偵測以免出錯
    try:
        # 清理欄位 (強制轉換數字)
        df["買賣超"] = pd.to_numeric(df["買賣超"].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    except KeyError:
        st.error("欄位名稱不符，請檢查證交所資料結構")
        st.stop()
    
    result = []
    for stock, g in df.groupby("證券代號"):
        g = g.sort_values("date")
        series = g["買賣超"].values
        if len(series) < 10: continue
        
        last3, last10 = series[-3:], series[-10:]
        
        # 這是您最原始的篩選邏輯，絕不改動
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "近10日買超": int(last10.sum())})

    out = pd.DataFrame(result)
    
    if not out.empty:
        st.success(f"完成：{len(out)} 檔")
        st.dataframe(out)
        selected = st.selectbox("請選擇代號查看圖表:", out['股票'].unique())
        if selected:
            draw_chart(selected)
    else:
        st.warning("目前市場無符合條件股票")
