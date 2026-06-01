import 
if st.button("🚀 啟動投信掃描", type="primary"):
    start_dt = (today_tw - timedelta(days=180)).strftime("%Y-%m-%d")
    df_raw = yf.download(tickers=total_pool, start=start_dt, group_by='ticker', progress=False)
    
    rows = []
    for s_id in total_pool:
        df = df_raw[s_id].dropna().copy()
        df.columns = [c.title() for c in df.columns]
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        
        # 簡易篩選條件
        if df['Close'].iloc[-1] > df['MA20'].iloc[-1]:
            st.session_state.sitc_stock_cache[s_id] = calculate_zigzag(df)
            rows.append({'股票代碼': s_id, '收盤': round(df['Close'].iloc[-1], 2)})
    
    st.session_state.sitc_report_df = pd.DataFrame(rows)

# ==========================================
# 4. 繪圖區 (mplfinance 專業版)
# ==========================================
if st.session_state.sitc_report_df is not None:
    active_list = list(st.session_state.sitc_stock_cache.keys())
    user_pick = st.selectbox("請選擇個股進行分析：", options=active_list)
    
    if user_pick:
        df = st.session_state.sitc_stock_cache[user_pick].tail(60)
        
        # 設定 mplfinance 風格
        mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit')
        s = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
        
        # 設定額外繪圖：均線與轉折點
        ap = [
            mpf.make_addplot(df['MA5'], color='orange', width=1),
            mpf.make_addplot(df['MA20'], color='purple', width=1),
            mpf.make_addplot(df['MA60'], color='blue', width=1)
        ]
        
        # 繪製圖表
        fig, axlist = mpf.plot(
            df, type='candle', style=s, addplot=ap,
            returnfig=True, figsize=(10, 6), volume=True
        )
        
        # 在主圖標註 H 與 B
        main_ax = axlist[0]
        for idx, row in df[df['Label'].notnull()].iterrows():
            x = df.index.get_loc(idx)
            is_h = row['Label'] == "H"
            main_ax.text(x, row['High'] if is_h else row['Low'], row['Label'],
                         color='white', weight='bold', ha='center',
                         bbox=dict(boxstyle="circle", fc="red" if is_h else "green"))
        
        st.pyplot(fig)
