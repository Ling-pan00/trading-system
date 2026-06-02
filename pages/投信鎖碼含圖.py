import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V9.2 實戰版", layout="wide")
st.title("📊 投信鎖碼股 V9.2（技術轉折整合版）")

# =========================
# 工具：欄位偵測
# =========================
def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c):
                return c
    return None

# =========================
# 1. 投信資料抓取 (原版邏輯)
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
# 2. 轉折圖繪製模組 (B版邏輯)
# =========================
def draw_zigzag_chart(ticker_code):
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d')
    
    # 確保代號正確
    df_chart = yf.download(f"{ticker_code}.TW", start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {ticker_code} 的資料，可能已下市或非台股。")
        return

    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()
    df_chart = df_chart.dropna().copy()

    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()

    zigzag_points = []
    df_chart['Label'] = None
    for g_id, group_data in df_chart.groupby('State_Group'):
        if g_id <= 2: continue
        if group_data['State'].iloc[0] == 1:
            idx = group_data['High'].idxmax()
            zigzag_points.append((df_chart.index.get_loc(idx), df_chart.loc[idx, 'High']))
            df_chart.loc[idx, 'Label'] = "H"
        else:
            idx = group_data['Low'].idxmin()
            zigzag_points.append((df_chart.index.get_loc(idx), df_chart.loc[idx, 'Low']))
            df_chart.loc[idx, 'Label'] = "B"

    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df_chart[['5MA', '10MA', '20MA']]) ]

    fig, axlist = mpf.plot(df_chart, type='candle', style=s, addplot=plots, returnfig=True, figsize=(10, 6), volume=True)
    main_ax = axlist[0]
    
    if len(zigzag_points) > 1:
        x, y = zip(*zigzag_points)
        main_ax.plot(x, y, color='gray', alpha=0.6, linewidth=1.5)
    
    for idx, row in df_chart[df_chart['Label'].notnull()].iterrows():
        x = df_chart.index.get_loc(idx)
        is_h = row['Label'] == "H"
        main_ax.text(x, row['High'] if is_h else row['Low'], row['Label'],
                     color='white', weight='bold', ha='center', va='center',
                     bbox=dict(boxstyle="circle,pad=0.3", fc="red" if is_h else "green", ec="none"))

    st.pyplot(fig)
    plt.close(fig)

# =========================
# 3. 主程式介面
# =========================
if st.button("🚀 開始 V9.2 分析"):
    df = load(30)
    if df.empty:
        st.error("未抓到資料")
        st.stop()

    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    
    # 處理字串轉數字的 KeyError 問題
    df[buy_col] = df[buy_col].replace(',', '', regex=True)
    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []
    for stock, g in df.groupby(stock_col):
        series = g.sort_values("date")[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        if (last3 < 0).sum() < 2 and last10.sum() > 20:
            result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})

    out = pd.DataFrame(result).sort_values("強度", ascending=False)
    
    if not out.empty:
        st.success(f"篩選出 {len(out)} 檔")
        selected = st.selectbox("請選擇查看轉折圖:", out['股票'].unique())
        if selected:
            draw_zigzag_chart(selected)
    else:
        st.warning("目前無符合條件股票")
