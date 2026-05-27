import datetime
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="台股便當選股器-多頭貼線版", layout="centered")
st.title("🚀 均線多頭 - 貼近5MA選股器")
st.write("自動篩選：月線(20MA)趨勢向上 ＆ 股價貼近5日線(5MA) $\pm8\%$ 的安全個股")


@st.cache_data(ttl=3600)
def get_all_taiwan_shares():
    stocks = {}
    modes = {"2": ".TW", "4": ".TWO"}
    for mode, extension in modes.items():
        url = f"http://isin.twse.com.tw/isin/C_public.jsp?strMode={mode}"
        try:
            res = requests.get(url, timeout=10)
            dfs = pd.read_html(res.text)
            df = dfs[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:]
            df = df[df["CFICode"] == "ESVUFR"]
            for item in df["有價證券代號及名稱"]:
                parts = item.split("\u3000")
                if len(parts) == 2:
                    stock_id, stock_name = parts[0], parts[1]
                    if len(stock_id) == 4 and stock_id.isdigit():
                        stocks[f"{stock_id}{extension}"] = stock_name
        except:
            continue
    return stocks


if st.button("🔍 開始全自動掃描全台股（多頭貼線）", type="primary"):
    stock_dict = get_all_taiwan_shares()
    qualified_stocks = []

    # 確保抓取足夠歷史資料
    end_date = datetime.date.today() + datetime.timedelta(days=1)
    start_date = end_date - datetime.timedelta(days=120)

    progress_bar = st.progress(0)
    status_text = st.empty()
    total_stocks = len(stock_dict)

    last_data_date = None
    error_count = 0  # 紀錄有幾檔股票被 Yahoo 拒絕

    for idx, (ticker, name) in enumerate(stock_dict.items()):
        current_progress = int((idx + 1) / total_stocks * 100)
        progress_bar.progress(current_progress)
        status_text.text(f"目前進度: {current_progress}% (正在掃描: {ticker} {name})")

        try:
            # 【核心修正】：加上 auto_adjust=True 修正復歸價格
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True,
            )

            # 如果抓下來是空的，代表被 Yahoo 暫時擋掉了
            if df.empty or len(df) < 25:
                error_count += 1
                continue

            # 處理多層索引(MultiIndex)問題，確保欄位名稱純淨
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 計算均線
            df["5MA"] = df["Close"].rolling(window=5).mean()
            df["20MA"] = df["Close"].rolling(window=20).mean()

            df = df.dropna(subset=["5MA", "20MA"])
            if len(df) < 2:
                continue

            today_data = df.iloc[-1]
            yesterday_data = df.iloc[-2]

            if last_data_date is None:
                last_data_date = df.index[-1].strftime("%Y-%m-%d")

            today_close = float(today_data["Close"])
            today_5ma = float(today_data["5MA"])
            today_20ma = float(today_data["20MA"])
            yesterday_20ma = float(yesterday_data["20MA"])

            # 策略條件
            is_20ma_up = today_20ma > yesterday_20ma
            bias_5ma = ((today_close - today_5ma) / today_5ma) * 100
            is_near_5ma = -8.0 <= bias_5ma <= 8.0

            if is_20ma_up and is_near_5ma:
                market_type = "上市" if ticker.endswith(".TW") else "上櫃"
                qualified_stocks.append(
                    {
                        "代號": ticker.split(".")[0],
                        "名稱": name,
                        "市場": market_type,
                        "今日收盤": round(today_close, 2),
                        "5MA乖離率(%)": round(bias_5ma, 2),
                        "月線位置": round(today_20ma, 2),
                    }
                )
        except:
            error_count += 1
            continue

    status_text.text("🎉 掃描完成！")

    if last_data_date:
        st.info(f"📅 目前掃描使用的最新數據日期為: **{last_data_date}**")

    # 如果失敗率太高，在網頁上提示用戶
    if error_count > (total_stocks * 0.5):
        st.warning(
            f"⚠️ 偵測到雲端主機目前連線受到限制（約 {error_count} 檔未能成功下載）。請稍等幾分鐘後點擊右下角 Manage App -> Rerun 重試。"
        )

    if qualified_stocks:
        result_df = pd.DataFrame(qualified_stocks)
        result_df["sort_key"] = result_df["5MA乖離率(%)"].abs()
        result_df = (
            result_df.sort_values(by="sort_key")
            .drop(columns=["sort_key"])
            .reset_index(drop=True)
        )

        st.success(f"✨ 共篩選出 {len(result_df)} 檔符合條件個股")
        st.dataframe(result_df, use_container_width=True)
    else:
        st.warning("市場中無符合「月線向上且貼近 5MA」之個股。")
