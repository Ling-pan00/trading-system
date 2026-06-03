import streamlit as st
import pandas as pd
import twstock
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="投信鎖碼 V10.1 (原策略版)", layout="wide")
st.title("投信鎖碼 V10.1 (原策略版)")

# --- 1. 你的原始選股核心 (完全沒動) ---
def load(days=30):
    all_df = []
    today = datetime.today()
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        url = f"https://www.twse.com.tw/rwd/zh/fund/TWT44U?date={d}&response=json"
        try:
            r = requests.get(url, timeout=10)
            data = r.json()
            if data.get("stat") == "OK":
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = d
                all_df.append(df)
        except: continue
        time.sleep(0.02)
        if len(all_df) >= days: break
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

def find(df, keys):
    for c in df.columns:
        for k in keys:
            if k in str(c): return c
    return None

if st.button("開始 V9.2"):
    df = load(30)
    stock_col = find(df, ["證券代號"])
    buy_col = find(df, ["買賣超"])
    df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
    
    result = []
    for stock, g in df.groupby(stock_col):
        g = g.sort_values("date")
        series = g[buy_col].values
        if len(series) < 10: continue
        last3, last10 = series[-3:], series[-10:]
        last3_sum, last10_sum = last3.sum(), last10.sum()
        if (last3 < 0).sum() >= 2 or last10_sum <= 0 or abs(last10_sum) < 20: continue
        result.append({"股票": stock, "強度": round(last3_sum / (abs(last10_sum) + 1), 4)})

    out = pd.DataFrame(result)
    st.session_state['final_out'] = out
    st.success(f"完成：{len(out)} 檔")
    st.dataframe(out)

# --- 2. 僅修正圖表區塊 (對接你產出的 out) ---
st.write("---")
st.subheader("🎯 轉折監測器")
if 'final_out' in st.session_state and not st.session_state['final_out'].empty:
    sel = st.selectbox("分析個股：", st.session_state['final_out']["股票"].astype(str).tolist())
    
    try:
        # 強制更新代碼，避免 ID 找不到
        twstock.__update_codes()
        stock = twstock.Stock(str(sel).strip())
        data = stock.fetch_3mo()
        
        if data:
            df_k = pd.DataFrame(data).set_index('date')
            df_k.columns = ['capacity', 'turnover', 'open', 'high', 'low', 'close', 'change', 'transaction']
            # 強制數值化，徹底解決 ValueError
            for c in ['open', 'high', 'low', 'close']:
                df_k[c] = pd.to_numeric(df_k[c], errors='coerce').fillna(0)
            
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', volume=True, returnfig=True, figsize=(10, 6))
            st.pyplot(fig)
        else:
            st.warning("該標的無歷史資料")
    except Exception as e:
        st.error(f"圖表繪製異常: {e}")
