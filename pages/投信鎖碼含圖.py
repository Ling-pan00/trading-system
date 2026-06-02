import streamlit as st
import pandas as pd
import requests
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V9.2 最終穩定版", layout="wide")
st.title("投信鎖碼 V9.2 (選股+技術圖表連動)")

# --- 1. 選股邏輯區 (完全遵照你的原始規則) ---
def load_and_filter():
    all_df = []
    today = datetime.today()
    for i in range(30):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=5)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.05)
    
    if not all_df: return pd.DataFrame()
    df = pd.concat(all_df, ignore_index=True)
    
    # 強制處理買賣超欄位 (解決篩選檔數異常)
    buy_col = [c for c in df.columns if '買賣超' in c][0]
    stock_col = [c for c in df.columns if '代號' in c][0]
    
    # 【關鍵：移除逗號，確保數值準確】
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        s = g[buy_col].values
        if len(s) < 10: continue
        
        last3, last10 = s[-3:], s[-10:]
        # 【你的原始邏輯：完全不變】
        if (last3 < 0).sum() >= 2 or last10.sum() <= 0 or abs(last10.sum()) < 20: continue
        
        result.append({"股票": stock, "強度": round(last3.sum() / (abs(last10.sum()) + 1), 4)})
    return pd.DataFrame(result).sort_values("強度", ascending=False)

# --- 2. 技術圖表繪圖區 (改用 matplotlib 避免 ValueError) ---
def plot_technical_chart(ticker):
    try:
        # 下載資料
        df = yf.download(f"{ticker}.TW", period="3mo", progress=False)
        if df.empty: df = yf.download(f"{ticker}.TWO", period="3mo", progress=False)
        
        # 計算 MA
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA10'] = df['Close'].rolling(10).mean()
        df['MA20'] = df['Close'].rolling(20).mean()

        # 繪圖
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df['Close'], color='black', alpha=0.3, label='Price')
        ax.plot(df.index, df['MA5'], label='5MA', color='orange')
        ax.plot(df.index, df['MA10'], label='10MA', color='blue')
        ax.plot(df.index, df['MA20'], label='20MA', color='purple')
        
        ax.set_title(f"{ticker} 技術走勢")
        ax.legend()
        ax.grid(True)
        st.pyplot(fig)
        plt.close(fig)
    except Exception as e:
        st.error("繪圖發生異常，請確認該股票代號是否有成交紀錄")

# --- 3. 執行介面 ---
if st.button("開始 V9.2"):
    st.session_state.out = load_and_filter()
    st.rerun()

if 'out' in st.session_state and not st.session_state.out.empty:
    st.success(f"成功篩選出 {len(st.session_state.out)} 檔股票")
    sel = st.selectbox("請選擇查看股票:", st.session_state.out["股票"].tolist())
    plot_technical_chart(sel)
    st.dataframe(st.session_state.out, use_container_width=True)
