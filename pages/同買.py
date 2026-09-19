import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="三大法人同步鎖碼股 V9.3", layout="wide")
st.title("🔥 三大法人（外資＋投信＋主力）同步鎖碼選股系統")

# =========================
# 📦 抓取 TWSE 三大法人日報 (T86)
# =========================
def get_institutional_day(date):
    url = f"https://www.twse.com.tw/exchangeReport/T86?date={date}&selectType=ALL&response=json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()

        if data.get("stat") != "OK" or not data.get("data"):
            return None

        df = pd.DataFrame(data["data"], columns=data["fields"])
        df["date"] = date
        return df
    except:
        return None

# =========================
# 📅 多日歷史資料載入
# =========================
def load_institutional_data(days=20):
    all_df = []
    today = datetime.today()

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    loaded_days = 0
    target_days = days
    
    for i in range(days * 2):
        d = (today - timedelta(days=i)).strftime("%Y%m%d")
        status_text.text(f"正在載入日期: {d} 的三大法人籌碼...")
        
        df = get_institutional_day(d)
        if df is not None and not df.empty:
            all_df.append(df)
            loaded_days += 1
            progress_bar.progress(min(loaded_days / target_days, 1.0))

        time.sleep(0.05)
        if loaded_days >= target_days:
            break

    status_text.empty()
    progress_bar.empty()

    if not all_df:
        return pd.DataFrame()

    return pd.concat(all_df, ignore_index=True)

# =========================
# 🔍 欄位智慧偵測模組
# =========================
def find_col(df, keywords):
    for c in df.columns:
        for k in keywords:
            if k in str(c):
                return c
    return None

# =========================
# 🚀 執行主按鈕
# =========================
if st.button("🚀 開始掃描三大法人同步鎖碼標的"):
    
    df = load_institutional_data(20)

    if df.empty:
        st.error("⚠️ 未能取得法人資料，請檢查網路或稍後再試。")
        st.stop()

    # 動態對應官方欄位名稱（避免大小寫或微調字串導致抓不到）
    stock_col = find_col(df, ["證券代號"])
    name_col = find_col(df, ["證券名稱"])
    foreign_col = find_col(df, ["外陸資買賣超股數(不含外資自營商)", "外資買賣超"])
    trust_col = find_col(df, ["投信買賣超股數", "投信買賣超"])
    dealer_col = find_col(df, ["自營商買賣超股數", "自營商買賣超"])

    if not stock_col or not foreign_col or not trust_col:
        st.error(f"❌ 欄位解析失敗！現有欄位：{list(df.columns)}")
        st.stop()

    # 數據清洗：移除千分位逗號與特殊符號
    for col in [foreign_col, trust_col, dealer_col]:
        if col and col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", "").str.replace("—", "0").str.replace("-", "0")
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    result = []

    # =========================
    # 🔥 籌碼共振與鎖碼核心運算
    # =========================
    for stock, g in df.groupby(stock_col):
        try:
            g = g.sort_values("date")
            s_name = g[name_col].iloc[-1] if name_col else ""

            f_series = g[foreign_col].values if foreign_col else [0]*len(g)
            t_series = g[trust_col].values if trust_col else [0]*len(g)
            d_series = g[dealer_col].values if dealer_col and dealer_col in g.columns else [0]*len(g)

            if len(f_series) < 5:
                continue

            # 計算近 3 日與近 10 日動向
            f_last3 = f_series[-3:].sum()
            t_last3 = t_series[-3:].sum()
            d_last3 = d_series[-3:].sum() if dealer_col else 0

            f_last10 = f_series[-10:].sum()
            t_last10 = t_series[-10:].sum()
            
            total_last3 = f_last3 + t_last3 + d_last3

            # 🎯 核心過濾條件：外資近3日買超 > 0 且 投信近3日買超 > 0（法人同步同買），且中期投信方向偏多
            if f_last3 > 0 and t_last3 > 0 and t_last10 > 0:
                
                # 綜合強度評分（加重投信籌碼權重）
                strength = (t_last3 * 2 + f_last3) / 1000

                result.append({
                    "代號": stock,
                    "名稱": s_name,
                    "綜合強度": round(strength, 2),
                    "近3日外資買超(股)": int(f_last3),
                    "近3日投信買超(股)": int(t_last3),
                    "近3日自營商買超(股)": int(d_last3),
                    "近3日三大法人合計(股)": int(total_last3),
                    "近10日投信累積(股)": int(t_last10)
                })
        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.warning("⚠️ 目前市場沒有符合「外資＋投信同步同買」條件的標的（可能近期盤勢較為觀望）。")
        st.stop()

    out = out.sort_values("綜合強度", ascending=False).reset_index(drop=True)

    st.success(f"🎉 篩選完成！共找到 {len(out)} 檔三大法人同步鎖碼標的：")
    st.dataframe(out, use_container_width=True)
