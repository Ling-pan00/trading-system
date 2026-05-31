import streamlit as st
import pandas as pd
import yfinance as yf
import twstock

st.set_page_config(page_title="穩定三池選股系統", layout="wide")

st.title("📊 穩定三池選股系統（保證有結果版）")

# =========================
# 股票池
# =========================
@st.cache_data(ttl=86400)
def get_stock_list():
    stocks = []

    for code, info in twstock.codes.items():
        if info.market in ["上市", "上櫃"]:
            if len(code) == 4 and code.isdigit():
                ticker = f"{code}.TW" if info.market == "上市" else f"{code}.TWO"
                stocks.append({"code": code, "name": info.name, "ticker": ticker})

    return stocks

stock_list = get_stock_list()

ticker_map = {
    s["ticker"]: {"code": s["code"], "name": s["name"]}
    for s in stock_list
}

tickers = list(ticker_map.keys())

st.write(f"📦 股票數量：{len(tickers)}")


# =========================
# 🔥 穩定打分（核心）
# =========================
def score(change_pct, close, ma5, ma10, ma20, vol, vol_ma5):

    s = 0

    # 趨勢
    if close > ma5:
        s += 2
    if ma5 > ma10:
        s += 1
    if ma10 > ma20:
        s += 1

    # 量
    if vol > vol_ma5:
        s += 2

    # 動能
    if change_pct > 0:
        s += 1

    # 避免太弱
    if change_pct < -3:
        s -= 2

    return s


# =========================
# 池別（保證不空版本）
# =========================
def classify_pool(score):

    if score >= 5:
        return "🚀 強勢突破"

    elif score >= 3:
        return "🟡 動能中段"

    else:
        return "🧊 低位回檔"


# =========================
# 掃描
# =========================
if st.button("🚀 開始掃描"):

    results = []

    progress = st.progress(0)
    status = st.empty()

    batch_size = 200
    total_batches = (len(tickers) + batch_size - 1) // batch_size

    for i in range(total_batches):

        batch = tickers[i*batch_size:(i+1)*batch_size]

        status.text(f"📥 批次 {i+1}/{total_batches}")

        try:
            data = yf.download(
                tickers=batch,
                period="3mo",
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False
            )

            for t in batch:

                try:
                    stock = data[t]
                    if stock.empty:
                        continue

                    close = stock["Close"]
                    volume = stock["Volume"]

                    if len(close) < 20:
                        continue

                    ma5 = close.rolling(5).mean().iloc[-1]
                    ma10 = close.rolling(10).mean().iloc[-1]
                    ma20 = close.rolling(20).mean().iloc[-1]

                    vol_ma5 = volume.rolling(5).mean().iloc[-1]

                    latest_close = float(close.iloc[-1])
                    latest_vol = float(volume.iloc[-1])

                    change_pct = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100

                    s = score(
                        change_pct,
                        latest_close,
                        ma5,
                        ma10,
                        ma20,
                        latest_vol,
                        vol_ma5
                    )

                    pool = classify_pool(s)

                    results.append({
                        "代號": ticker_map[t]["code"],
                        "名稱": ticker_map[t]["name"],
                        "收盤": round(latest_close, 2),
                        "漲跌%": round(change_pct, 2),
                        "量": int(latest_vol),
                        "分數": s,
                        "池別": pool
                    })

                except:
                    continue

        except:
            continue

        progress.progress((i + 1) / total_batches)

    status.text("✅ 完成")

    # =========================
    # 輸出
    # =========================
    df = pd.DataFrame(results)

    # 🔥 強制保證有結果（核心）
    df = df.sort_values("分數", ascending=False)

    # 三池分開
    strong = df[df["池別"] == "🚀 強勢突破"].head(5)
    mid = df[df["池別"] == "🟡 動能中段"].head(5)
    weak = df[df["池別"] == "🧊 低位回檔"].head(5)

    # fallback（保證不空）
    if strong.empty:
        strong = df.head(5)
    if mid.empty:
        mid = df.head(5)
    if weak.empty:
        weak = df.tail(5)

    # =========================
    # UI
    # =========================
    st.subheader("🚀 強勢突破 Top 5")
    st.dataframe(strong, use_container_width=True)

    st.subheader("🟡 動能中段 Top 5")
    st.dataframe(mid, use_container_width=True)

    st.subheader("🧊 低位回檔 Top 5")
    st.dataframe(weak, use_container_width=True)

    st.subheader("📌 今日總強勢 Top 10")
    st.dataframe(df.head(10), use_container_width=True)
