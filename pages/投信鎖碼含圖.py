import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V9.2", layout="wide")
st.title("投信鎖碼股 V9.2（實戰版）")

# =========================
# A 程式碼：原版邏輯 (完全不動)
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
# B 程式碼：增強版繪圖模組 (加入代號自動修復)
# =========================
def draw_zigzag_chart(ticker_code):
    # 嘗試兩種代號格式
    targets = [f"{ticker_code}.TW", str(ticker_code)]
    df_chart = pd.DataFrame()
    
    for t in targets:
        temp_df = yf.download(t, period="3mo", progress=False)
        if not temp_df.empty:
            df_chart = temp_df
            break
            
    if df_chart.empty:
        st.error(f"⚠️ 找不到代號 {ticker_code} 的市場資料，請確認該標的是否為台股上市櫃公司。")
        return

    # 標準化欄位
    df_chart.columns = df_chart.columns.get_level_values(0) if isinstance(df_chart.columns, pd.MultiIndex) else df_chart.columns
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna().copy()

    # 轉折計算 (維持您要的樣式)
    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()
    zigzag_points, df_chart['Label'] = [], None
    for g_id, group in df_chart.groupby('State_Group'):
        if g_id <= 2: continue
        if group['State'].iloc[0] == 1:
            idx = group['High'].idxmax(); zigzag_points.append((df_chart.index.get_loc(idx), df_chart.loc[idx, 'High'])); df_chart.loc[idx, 'Label'] = "H"
        else:
            idx = group['Low'].idxmin(); zigzag_points.append((df_chart.index.get_loc(idx), df_chart.loc[idx, 'Low'])); df_chart.loc[idx, 'Label'] = "B"

    # 繪圖
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    fig, axlist = mpf.plot(df_chart, type='candle', style=s, addplot=[mpf.make_addplot(df_chart[['5MA', '10MA', '20MA']])], returnfig=True, figsize=(10, 6), volume=True)
    
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points); axlist[0].plot(x, y, color='black', alpha=0.5, linewidth=1.5)
    for idx, row in df_chart[df_chart['Label'].notnull()].iterrows():
        x = df_chart.index.get_loc(idx); is_h = row['Label'] == "H"
        axlist[0].text(x, row['High'] if is_h else row['Low'], row['Label'], color='white', weight='bold', ha='center', va='center', bbox=dict(boxstyle="circle,pad=0.3", fc="red" if is_h else "green", ec="none"))
    st.pyplot(fig); plt.close(fig)

# =========================
# 主程式 (策略完全未動)
# =========================
if st.button("開始 V9.2"):
    df = load(30)
    if df.empty: st.stop()
    stock_col, buy_col = find(df, ["證券代號"]), find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        if (last3 < 0).sum() >= 2: continue
        if last10.sum() <= 0: continue
        if abs(last10.sum()) < 20: continue
        result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
        
    out = pd.DataFrame(result).sort_values("強度", ascending=False)
    st.dataframe(out)
    
    selected = st.selectbox("選擇股票看圖:", out['股票'].unique())
    if selected: draw_zigzag_chart(selected)
