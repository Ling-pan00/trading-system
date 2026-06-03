import streamlit as st
import pandas as pd
import yfinance as yf
import twstock
import numpy as np
import mplfinance as mpf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta


#

# ==========================================
# 🎨 轉折 K 線圖繪製模組 (設定為 3 個月區間)
# ==========================================
def draw_zigzag_chart(ticker_code, stock_name):
    """繪製 3 個月區間的 5MA 轉折波段圖"""
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=90)).strftime('%Y-%m-%d') # 精準 3 個月範圍
    
    df_chart = yf.download(ticker_code, start=start_date, end=end_date, progress=False)
    
    if df_chart.empty:
        st.error(f"⚠️ 無法取得 {stock_name}({ticker_code}) 的圖表數據。")
        return

    # 處理 yfinance 多國資料庫結構
    if isinstance(df_chart.columns, pd.MultiIndex):
        df_chart.columns = df_chart.columns.get_level_values(0)

    # 1. 計算均線
    df_chart['5MA'] = df_chart['Close'].rolling(window=5).mean()
    df_chart['10MA'] = df_chart['Close'].rolling(window=10).mean()
    df_chart['20MA'] = df_chart['Close'].rolling(window=20).mean()

    df_chart['Close'] = pd.to_numeric(df_chart['Close'], errors='coerce')
    df_chart['High'] = pd.to_numeric(df_chart['High'], errors='coerce')
    df_chart['Low'] = pd.to_numeric(df_chart['Low'], errors='coerce')

    df_chart = df_chart.dropna(subset=['Close', '5MA', '20MA']).copy()

    # 2. 轉折波段邏輯
    df_chart['State'] = np.where(df_chart['Close'] > df_chart['5MA'], 1, -1)
    df_chart['State_Group'] = (df_chart['State'] != df_chart['State'].shift()).cumsum()

    zigzag_points = []
    grouped = df_chart.groupby('State_Group')
    group_ids = sorted(df_chart['State_Group'].unique())

    for g_id in group_ids:
        group_data = grouped.get_group(g_id)
        state = group_data['State'].iloc[0]
        if g_id <= 2: continue
        if state == 1:
            highest_idx = group_data['High'].idxmax()
            zigzag_points.append((df_chart.index.get_loc(highest_idx), df_chart.loc[highest_idx, 'High']))
            df_chart.loc[highest_idx, 'Label'] = "H"
        else:
            lowest_idx = group_data['Low'].idxmin()
            zigzag_points.append((df_chart.index.get_loc(lowest_idx), df_chart.loc[lowest_idx, 'Low']))
            df_chart.loc[lowest_idx, 'Label'] = "B"

    # 3. 取得均線數據與箭頭
    def get_ma_details(col_name):
        now = df_chart[col_name].iloc[-1]
        pre = df_chart[col_name].iloc[-2]
        arrow = "▲" if now >= pre else "▼"
        return f"{now:.2f} {arrow}"

    st.markdown(f"#### 📈 {stock_name} ({ticker_code}) — 3個月 5MA 轉折波段圖")
    st.markdown(f"""
        <div style="
            background-color: #f8f9fa; 
            padding: 10px 15px; 
            border-radius: 5px; 
            margin-top: 5px; 
            margin-bottom: 10px; 
            font-family: monospace; 
            font-size: 15px; 
            font-weight: bold;
            border-left: 5px solid #6c757d;
        ">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_details('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_details('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_details('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    # 4. 繪製圖表
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    s_style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')

    plots = [
        mpf.make_addplot(df_chart['5MA'], color='orange', width=1),
        mpf.make_addplot(df_chart['10MA'], color='blue', width=1),
        mpf.make_addplot(df_chart['20MA'], color='purple', width=1)
    ]

    fig, axlist = mpf.plot(
        df_chart, type='candle', style=s_style, addplot=plots, 
        returnfig=True, figsize=(12, 6), volume=True,
        panel_ratios=(4,1)
    )
    
    main_ax = axlist[0]

    # 5. 連接轉折線
    if len(zigzag_points) > 1:
        x_coords, y_coords = zip(*zigzag_points)
        main_ax.plot(x_coords, y_coords, color='black', alpha=0.5, linewidth=1.5, zorder=3)

    # 6. 標註 H/B
    for idx, row in df_chart[df_chart['Label'].notnull()].iterrows():
        x = df_chart.index.get_loc(idx)
        is_h = row['Label'] == "H"
        main_ax.text(x, row['High' if is_h else 'Low'], row['Label'],
                    color='red' if is_h else 'green', weight='bold',
                    ha='center', va='bottom' if is_h else 'top',
                    bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))

    st.pyplot(fig)
    plt.close

# ==========================================
# 📊 畫面渲染模組與【按鈕與下拉選單雙向聯動機制】
# ==========================================
for pool_name in ["🔴 第四池", "🔵 第三池", "🟠 第二池", "🟡 第一池"]:
    if f"pool_{pool_name}" in st.session_state:
        saved_df = st.session_state[f"pool_{pool_name}"]
        st.subheader(f"📊 策略精選名單 - {pool_name}")
        
        if not saved_df.empty:
            # 呈現給使用者看的前台表格
            display_df = saved_df.drop(columns=["ticker"])
            st.dataframe(display_df, use_container_width=True)
            
            # 生成股票選單選項 (與 DataFrame 索引完全對應)
            stock_options = [f"{row['代號']} {row['名稱']}" for _, row in saved_df.iterrows()]
            
            # 初始化該池別的 index 狀態
            if f"idx_{pool_name}" not in st.session_state:
                st.session_state[f"idx_{pool_name}"] = 0
                
            current_idx = st.session_state[f"idx_{pool_name}"]

            # 🛠️ 建立控制列：左按鈕、下拉選單、右按鈕
            st.write(f"🔍 **切換檢視 K 線圖（共 {len(stock_options)} 檔）：**")
            btn_col1, sel_col, btn_col2 = st.columns([1, 4, 1])
            
            with btn_col1:
                # 點擊「上一檔」
                if st.button("⏮️ 上一檔", key=f"prev_btn_{pool_name}", use_container_width=True):
                    if current_idx > 0:
                        st.session_state[f"idx_{pool_name}"] = current_idx - 1
                        st.rerun()

            with sel_col:
                # 🔥【修復線】修正了外雙引號、內單引號的寫法，解決程式卡死問題
                selected_stock = st.selectbox(
                    f"選擇股票：", 
                    stock_options, 
                    index=st.session_state[f"idx_{pool_name}"],
                    key=f"select_{pool_name}_v2_{st.session_state[f'idx_{pool_name}']}",
                    label_visibility="collapsed"
                )
                # 如果使用者手動下拉選別檔，也要同步回狀態中
                new_idx = stock_options.index(selected_stock)
                if new_idx != current_idx:
                    st.session_state[f"idx_{pool_name}"] = new_idx
                    st.rerun()

            with btn_col2:
                # 點擊「下一檔」
                if st.button("⏭️ 下一檔", key=f"next_btn_{pool_name}", use_container_width=True):
                    if current_idx < len(stock_options) - 1:
                        st.session_state[f"idx_{pool_name}"] = current_idx + 1
                        st.rerun()
            
            # 依據最終確定的 index 撈出後台對應的正確 ticker 並繪圖
            final_idx = st.session_state[f"idx_{pool_name}"]
            target_row = saved_df.iloc[final_idx]
            
            # 繪製圖形
            draw_zigzag_chart(target_row["ticker"], target_row["名稱"])
        else:
            st.info("此池目前無符合條件股票")
