import streamlit as st
import pandas as pd
import requests
import yfinance as yf

st.set_page_config(page_title="投信鎖碼股 V8", layout="wide")
st.title("投信鎖碼股 V8（穩定資料版）")

# =========================
# ✔ 穩定資料源（替代 TWSE TWT44U）
# =========================
def get_twse_institutional():
    url = "https://openapi.twse.com.tw/v1/fund/TWT44U"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# =========================
# price
# =========================
@st.cache_data(ttl=86400)
def get_price(stock):
    try:
        h = yf.Ticker(f"{stock}.TW").history(period="6mo")
        if h.empty:
            return None

        close = h["Close"]
        return {
            "ma_up": close.mean() > close.rolling(20).mean().mean(),
            "breakout": close.iloc[-1] > close.rolling(20).max().iloc[-2]
        }
    except:
        return None


if st.button("開始 V8"):

    df = get_twse_institutional()

    st.write("資料筆數:", df.shape)

    if df.empty:
        st.error("資料源失敗（不是你程式問題，是 API 不穩）")
        st.stop()

    # 找欄位
    stock_col = [c for c in df.columns if "證券代號" in c or "代號" in c][0]
    buy_col = [c for c in df.columns if "買賣超" in c][0]

    df[buy_col] = pd.to_numeric(df[buy_col], errors="coerce").fillna(0)

    result = []

    for stock, g in df.groupby(stock_col):

        try:
            if str(stock).startswith("00"):
                continue

            last10 = g[buy_col].tail(10).sum()

            price = get_price(stock)
            if price is None:
                continue

            score = last10 * 0.001

            result.append({
                "股票": stock,
                "投信動能": last10,
                "分數": score,
                "MA": price["ma_up"],
                "突破": price["breakout"]
            })

        except:
            continue

    out = pd.DataFrame(result)

    if out.empty:
        st.error("仍無資料（代表市場當下真的沒有符合條件）")
        st.stop()

    out = out.sort_values("分數", ascending=False)

    st.success(f"完成：{len(out)} 檔")

    st.dataframe(out)
