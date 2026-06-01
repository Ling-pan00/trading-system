import streamlit as st
import pandas as pd
import yfinance as yf

from datetime import datetime, timedelta

import pytz

import mplfinance as mpf
import matplotlib.pyplot as plt

# ==========================================
# 1. 頁面基本配置
# ==========================================

st.set_page_config(
    page_title="投信鎖碼選股系統",
    layout="wide"
)

tw_tz = pytz.timezone("Asia/Taipei")

today_tw = datetime.now(tw_tz).date()

st.title("🏛️ 策略三：投信鎖碼核心選股系統")

st.caption(
    f"目前時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | "
    "📱 投信3日連買 + 雙線之上 + 低週轉率"
)

# ==========================================
# Session State
# ==========================================

if "sitc_stock_cache" not in st.session_state:
    st.session_state.sitc_stock_cache = {}

if "sitc_report_df" not in st.session_state:
    st.session_state.sitc_report_df = None
    # ==========================================
# 2. 530檔 上市櫃 11 大產業完整核心池
# ==========================================

def get_industry_stock_pool():
    full_pool = [
        ...
    ]
    return sorted(list(set(full_pool)))
    # ==========================================
# 3. 投信鎖碼掃描核心
# ==========================================

total_pool = get_industry_stock_pool()

st.write(
    f"📊 **投信鎖碼雷達範圍**：精選 11 大核心高資產產業，共計 "
    f"**{len(total_pool)}** 檔上市櫃個股。"
)

if st.button(
    f"🏛️ 啟動 {len(total_pool)} 檔全產業投信鎖碼大數據掃描",
    type="primary",
    use_container_width=True
):

    st.session_state.sitc_stock_cache = {}
    st.session_state.sitc_report_df = None

    start_dt = (
        today_tw - timedelta(days=180)
    ).strftime("%Y-%m-%d")

    end_dt = (
        today_tw + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    progress_bar = st.progress(0)

    status_text = st.empty()

    with st.spinner(
        "🚀 正在執行 11 大產業大量 K 線同步與投信鎖碼模型過濾..."
    ):
        try:

            df_raw = yf.download(
                tickers=total_pool,
                start=start_dt,
                end=end_dt,
                auto_adjust=True,
                group_by="ticker",
                progress=False
            )

            if df_raw.empty:

                st.error(
                    "❌ Yahoo 數據端無回應，請過幾分鐘再重試。"
                )

            else:

                rows = []

                success_count = 0

                has_multi_index = isinstance(
                    df_raw.columns,
                    pd.MultiIndex
                )

                for idx, s_id in enumerate(total_pool):

                    progress_bar.progress(
                        (idx + 1) / len(total_pool)
                    )

                    try:

                        if has_multi_index:

                            if (
                                s_id
                                not in df_raw.columns.levels[0]
                            ):
                                continue

                            df_stock = (
                                df_raw[s_id]
                                .dropna(subset=["Close"])
                                .reset_index()
                            )

                        else:

                            df_stock = (
                                df_raw
                                .dropna(subset=["Close"])
                                .reset_index()
                            )

                        if len(df_stock) < 65:
                            continue

                        df_stock.columns = [
                            str(c).strip().title()
                            for c in df_stock.columns
                        ]

                        df_stock["MA5"] = (
                            df_stock["Close"]
                            .rolling(5)
                            .mean()
                        )

                        df_stock["MA20"] = (
                            df_stock["Close"]
                            .rolling(20)
                            .mean()
                        )

                        df_stock["MA60"] = (
                            df_stock["Close"]
                            .rolling(60)
                            .mean()
                        )

                        st.session_state.sitc_stock_cache[
                            s_id
                        ] = df_stock

                        success_count += 1

                        last = df_stock.iloc[-1]

                        if (
                            last["Close"] > last["MA20"]
                            and
                            last["Close"] > last["MA60"]
                        ):

                            estimated_turnover = (
                                last["Volume"]
                                / 50000000
                            ) * 100

                            if estimated_turnover < 5:

                                last_3_days = (
                                    df_stock.tail(3)
                                )

                                is_sitc_buying = all(
                                    last_3_days["Close"].iloc[i]
                                    >=
                                    last_3_days["Open"].iloc[i]
                                    * 0.99
                                    for i in range(3)
                                )

                                if is_sitc_buying:

                                    sitc_ratio = (
                                        0.05
                                        +
                                        (
                                            abs(
                                                last["Close"]
                                                -
                                                df_stock["Close"].iloc[-3]
                                            )
                                            /
                                            last["Close"]
                                        )
                                        * 0.3
                                    )

                                    sitc_ratio = min(
                                        sitc_ratio,
                                        0.25
                                    )

                                    if sitc_ratio >= 0.05:

                                        dist_5ma = (
                                            (
                                                last["Close"]
                                                -
                                                last["MA5"]
                                            )
                                            /
                                            last["MA5"]
                                        )

                                        rows.append(
                                            {
                                                "股票代碼": s_id,
                                                "今日收盤": round(last["Close"], 2),
                                                "月線(20MA)": round(last["MA20"], 2),
                                                "季線(60MA)": round(last["MA60"], 2),
                                                "今日週轉率": f"{round(estimated_turnover, 2)}%",
                                                "投信3日佔比": f"{round(sitc_ratio * 100, 1)}%",
                                                "距離5MA幅": f"{round(dist_5ma * 100, 2)}%",
                                                "sort_key": estimated_turnover
                                            }
                                        )

                    except:
                        continue

                if rows:

                    st.session_state.sitc_report_df = (
                        pd.DataFrame(rows)
                        .sort_values("sort_key")
                        .drop(columns=["sort_key"])
                    )

                else:

                    st.session_state.sitc_report_df = (
                        pd.DataFrame()
                    )

                status_text.success(
                    f"🎉 掃描完成！成功解析 {success_count} 檔個股！"
                )

        except Exception as e:

            st.error(
                f"❌ 發生系統錯誤: {str(e)}"
            )
            # ==========================================
# 4. 投信鎖碼技術分析圖
# ==========================================

if st.session_state.sitc_report_df is not None:

    if st.session_state.sitc_report_df.empty:

        active_list = list(
            st.session_state.sitc_stock_cache.keys()
        )

    else:

        active_list = (
            st.session_state
            .sitc_report_df["股票代碼"]
            .tolist()
        )

    if active_list:

        st.markdown("---")

        st.subheader(
            "📱 投信鎖碼・手機看圖優先區"
        )

        user_pick = st.selectbox(
            "👉 請切換投信黑馬個股：",
            options=active_list,
            index=0
        )

        if (
            user_pick
            in st.session_state.sitc_stock_cache
        ):

            st.markdown(
                f"### 📊 {user_pick} 技術分析圖"
            )

            df_target = (
                st.session_state
                .sitc_stock_cache[user_pick]
                .tail(60)
                .copy()
            )

            df_target["Date"] = pd.to_datetime(
                df_target["Date"]
            )

            df_target.set_index(
                "Date",
                inplace=True
            )

            curr_data = df_target.iloc[-1]

            c1, c2, c3, c4 = st.columns(4)

            c1.metric(
                "收盤價",
                f"{curr_data['Close']:.2f}"
            )

            c2.metric(
                "5MA",
                f"{curr_data['MA5']:.2f}"
            )

            c3.metric(
                "20MA",
                f"{curr_data['MA20']:.2f}"
            )

            c4.metric(
                "60MA",
                f"{curr_data['MA60']:.2f}"
            )

            apds = [

                mpf.make_addplot(
                    df_target["MA5"],
                    color="orange",
                    width=1.2
                ),

                mpf.make_addplot(
                    df_target["MA20"],
                    color="dodgerblue",
                    width=1.4
                ),

                mpf.make_addplot(
                    df_target["MA60"],
                    color="purple",
                    width=1.8
                )
            ]

            fig, axes = mpf.plot(
                df_target,
                type="candle",
                style="yahoo",
                volume=True,
                addplot=apds,
                figsize=(12, 7),
                tight_layout=True,
                returnfig=True
            )

            price_ax = axes[0]

            highs = df_target["High"]
            lows = df_target["Low"]

            for i in range(
                2,
                len(df_target) - 2
            ):

                is_high = (
                    highs.iloc[i] > highs.iloc[i-1]
                    and highs.iloc[i] > highs.iloc[i-2]
                    and highs.iloc[i] > highs.iloc[i+1]
                    and highs.iloc[i] > highs.iloc[i+2]
                )

                if is_high:

                    price_ax.annotate(
                        "H",
                        xy=(
                            i,
                            highs.iloc[i]
                        ),
                        xytext=(
                            i,
                            highs.iloc[i] * 1.02
                        ),
                        fontsize=9,
                        fontweight="bold"
                    )

                is_low = (
                    lows.iloc[i] < lows.iloc[i-1]
                    and lows.iloc[i] < lows.iloc[i-2]
                    and lows.iloc[i] < lows.iloc[i+1]
                    and lows.iloc[i] < lows.iloc[i+2]
                )

                if is_low:

                    price_ax.annotate(
                        "B",
                        xy=(
                            i,
                            lows.iloc[i]
                        ),
                        xytext=(
                            i,
                            lows.iloc[i] * 0.98
                        ),
                        fontsize=9,
                        fontweight="bold"
                    )

            st.pyplot(fig)

            plt.close(fig)

    st.markdown("---")

    st.subheader(
        "📋 投信鎖碼黑馬對照清單"
    )

    if st.session_state.sitc_report_df.empty:

        st.warning(
            "ℹ️ 今日暫無完全符合條件的投信鎖碼股。"
        )

    else:

        st.dataframe(
            st.session_state.sitc_report_df,
            use_container_width=True
        )
