import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(layout="wide")
st.title("投信鎖碼 V9.2 最終修復版")

# --- 核心邏輯 ---
def load_data(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("stat") == "OK":
                temp_df = pd.DataFrame(data["data"], columns=data["fields"])
                temp_df["date"] = d
                all_df.append(temp_df)
        except: continue
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

def plot_chart(ticker):
    ticker_str = str(ticker).strip()
    # 自動偵測上市/上櫃
    for s in ['.TW', '.TWO']:
        df = yf.download(f"{ticker_str}{s}", period="3mo", progress=False)
        if not df.empty and len(df) > 10: break
    
    if df.empty:
        st.error(f"無法取得 {ticker} 數據")
        return
    
    # 清洗：確保 index 是時間，且欄位為數值
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df.apply(pd.to_numeric, errors='coerce').dropna()
    
    # 計算 MA
    for m in [5, 10, 20]: df[f'MA{m}'] = df['Close'].rolling(m).mean()
    
    apds = [mpf.make_addplot(df[[f'MA{m}' for m in [5, 10, 20]]])]
    fig, ax = mpf.plot(df, type='candle', style='charles', addplot=apds, returnfig=True, figsize=(10, 5))
    st.pyplot(fig)
    plt.close(fig)

# --- 操作介面 ---
if st.button("開始 V9.2"):
    raw_df = load_data(30)
    if raw_df.empty:
        st.error("未抓到任何資料，請稍後再試")
    else:
        # 動態尋找欄位
        s_col = [c for c in raw_df.columns if '代號' in c][0]
        b_col = [c for c in raw_df.columns if '買賣超' in c][0]
        
        raw_df[b_col] = pd.to_numeric(raw_df[b_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        results = []
        for stock, g in raw_df.groupby(s_col):
            g = g.sort_values("date")
            s = g[b_col].values
            if len(s) < 10: continue
            
            # 原始策略條件
            if (s[-3:] < 0).sum() >= 2 or s[-10:].sum() <= 0 or abs(s[-10:].sum()) < 20: continue
            results.append({"股票": stock, "強度": round(s[-3:].sum() / (abs(s[-10:].sum()) + 1), 4)})
        
        st.session_state.final_out = pd.DataFrame(results).sort_values("強度", ascending=False)
        st.rerun()

if 'final_out' in st.session_state and not st.session_state.final_out.empty:
    st.success(f"篩選出 {len(st.session_state.final_out)} 檔")
    sel = st.selectbox("選擇股票:", st.session_state.final_out["股票"].tolist())
    plot_chart(sel)
    st.dataframe(st.session_state.final_out)
