import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼股 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（平衡實戰版）")

# =========================
# 輔助：轉折點計算函數
# =========================
def get_zigzag_points(df, pct=0.05):
    points = []
    if 'Close' not in df.columns: return points
    data = df['Close'].values
    for i in range(1, len(data) - 1):
        if data[i] > data[i-1] and data[i] > data[i+1]:
            points.append((df.index[i], data[i], 'H'))
        elif data[i] < data[i-1] and data[i] < data[i+1]:
            points.append((df.index[i], data[i], 'L'))
    return points

# =========================
# 資料抓取與處理函數
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

# =========================
# 主程式
# =========================
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty:
        st.error("沒有抓到資料")
        st.stop()

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
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
                "穩定度": round(last10_sum / (abs(last3_sum) + 1), 4)
            })
        except: continue

    out = pd.DataFrame(result)
    if out.empty:
        st.warning("目前市場沒有明顯投信鎖碼")
        st.stop()

    out = out.sort_values("強度", ascending=False)
    st.success(f"完成：{len(out)} 檔")
    st.dataframe(out)
    st.session_state['final_out'] = out

# =========================
# 轉折圖分析 (加入了錯誤處理)
# =========================
if 'final_out' in st.session_state:
    st.write("---")
    st.subheader("🎯 轉折監測器")
    final_out = st.session_state['final_out']
    sel = st.selectbox("分析個股：", final_out["股票"].tolist())
    
    ticker = f"{sel}.TW"
    df_k = yf.download(ticker, period="3mo", progress=False)
    
    # 增加資料有效性檢查
    if df_k is not None and not df_k.empty:
        if isinstance(df_k.columns, pd.MultiIndex): 
            df_k.columns = df_k.columns.get_level_values(0)
            
        df_k['5MA'] = df_k['Close'].rolling(5).mean()
        df_k['10MA'] = df_k['Close'].rolling(10).mean()
        df_k['20MA'] = df_k['Close'].rolling(20).mean()
        
        l = df_k.iloc[-1]
        st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace;">
                5MA: {l['5MA']:.2f} | 10MA: {l['10MA']:.2f} | 20MA: {l['20MA']:.2f}
            </div>
        """, unsafe_allow_html=True)
        
        fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                               addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
        
        ax = axlist[0]
        for idx, val, lbl in get_zigzag_points(df_k):
            if idx in df_k.iloc[-90:].index:
                ax.annotate(lbl, (df_k.index.get_loc(idx), val), ha='center', color='red' if lbl=='H' else 'green', weight='bold')
        st.pyplot(fig)
    else:
        st.error(f"無法獲取 {ticker} 的資料，請稍後再試或檢查網路連線。")
