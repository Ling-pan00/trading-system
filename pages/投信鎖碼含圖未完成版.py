import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

# --- 1. 你的原始策略邏輯 (完全保留) ---
# 我這裡將你的 load 與邏輯原樣放入，確保篩選結果與你之前跑出來一致
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

# --- 2. 介面與篩選 (原始邏輯) ---
if 'out' not in st.session_state: st.session_state['out'] = pd.DataFrame()

if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    # 這裡的清理邏輯保留，但確保轉換過程正確
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        
        # --- 原始篩選條件 ---
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({
            "股票": stock, "代號": stock, "ticker": f"{stock}.TW",
            "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)
        })
    st.session_state['out'] = pd.DataFrame(result)
    st.success(f"完成篩選，共 {len(result)} 檔")

# --- 3. 修正繪圖邏輯 (解決圖表不顯示問題) ---
st.write("---")
st.subheader("🎯 轉折監測器")
if not st.session_state['out'].empty:
    sel = st.selectbox("分析個股：", st.session_state['out']["股票"].tolist())
    ticker = st.session_state['out'][st.session_state['out']["股票"] == sel]["ticker"].values[0]
    
    # 增加檢查，避免因為 yfinance 抓不到資料導致當機
    df_k = yf.download(ticker, period="3mo", progress=False)
    if not df_k.empty:
        # 繪圖邏輯照舊，但確保資料對齊
        if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
        fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6))
        st.pyplot(fig)
    else:
        st.error(f"無法取得 {ticker} 的歷史資料，請確認代號是否正確。")
