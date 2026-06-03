import streamlit as st
import pandas as pd
import twstock
import mplfinance as mpf
import requests
from datetime import datetime, timedelta
import time

# 設定網頁佈局
st.set_page_config(page_title="投信鎖碼 V9.8 穩定版", layout="wide")
st.title("投信鎖碼 V9.8 (原策略穩定版)")

# --- 1. Session 初始化 ---
if 'final_out' not in st.session_state:
    st.session_state['final_out'] = pd.DataFrame()

# --- 2. 資料載入核心 ---
@st.cache_data(ttl=3600)
def load_data():
    all_df = []
    today = datetime.today()
    for i in range(60):
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
        time.sleep(0.05)
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# --- 3. 選股邏輯 ---
if st.button("🚀 開始執行選股"):
    with st.spinner('正在執行策略分析...'):
        df = load_data()
        if not df.empty:
            try:
                # 欄位偵測與轉換
                stock_col = [c for c in df.columns if '證券代號' in c][0]
                buy_col = [c for c in df.columns if '買賣超' in c][0]
                df[buy_col] = pd.to_numeric(df[buy_col].astype(str).str.replace(',', ''), errors="coerce").fillna(0)
                
                result = []
                for stock, g in df.groupby(stock_col):
                    g = g.sort_values("date")
                    series = g[buy_col].values
                    if len(series) < 10: continue
                    
                    # --- 你的原始策略邏輯 ---
                    last3, last10 = series[-3:], series[-10:]
                    last3_sum, last10_sum = last3.sum(), last10.sum()
                    if (last3 < 0).sum() >= 2 or last10_sum <= 0 or abs(last10_sum) < 20: continue
                    
                    result.append({"股票": stock, "強度": round(last3_sum / (abs(last10_sum) + 1), 4)})
                
                out = pd.DataFrame(result)
                if not out.empty:
                    st.session_state['final_out'] = out.sort_values("強度", ascending=False)
                    st.success(f"完成！共 {len(out)} 檔")
                    st.dataframe(st.session_state['final_out'])
                else:
                    st.warning("目前市場無符合條件標的")
            except Exception as e:
                st.error(f"篩選邏輯錯誤: {e}")

# --- 4. 轉折監測器 (修正 Value Error) ---
st.write("---")
st.subheader("🎯 轉折監測器")
if not st.session_state['final_out'].empty:
    options = st.session_state['final_out']["股票"].astype(str).tolist()
    sel = st.selectbox("請選擇個股：", options)
    
    try:
        # 強制更新股票資料庫以防找不到代碼
        twstock.__update_codes()
        stock = twstock.Stock(str(sel).strip())
        df_k = pd.DataFrame(stock.fetch_3mo())
        
        if not df_k.empty:
            df_k = df_k.set_index('date')
            df_k.columns = ['capacity', 'turnover', 'open', 'high', 'low', 'close', 'change', 'transaction']
            # 強制轉換所有價格為浮點數，解決 ValueError
            for c in ['open', 'high', 'low', 'close']:
                df_k[c] = pd.to_numeric(df_k[c], errors='coerce').fillna(0.0)
            
            fig, ax = mpf.plot(df_k.iloc[-90:], type='candle', volume=True, returnfig=True, figsize=(10, 6))
            st.pyplot(fig)
        else:
            st.error("該個股無歷史資料。")
    except Exception as e:
        st.error(f"繪圖異常: {e} (可能是代碼庫未對齊)")
else:
    st.info("請先執行篩選標的。")
