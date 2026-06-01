import '] = None
    zigzag_points = []
    for g_id, group in df.groupby('State_Group'):
        if g_id <= 2: continue
        if group['State'].iloc[0] == 1:
            idx = group['High'].idxmax()
            df.at[idx, 'Label'] = "H"
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'High']))
        else:
            idx = group['Low'].idxmin()
            df.at[idx, 'Label'] = "B"
            zigzag_points.append((df.index.get_loc(idx), df.loc[idx, 'Low']))

    # 【HTML 看板】
    def get_ma_info(col):
        now, pre = df[col].iloc[-1], df[col].iloc[-2]
        return f"{now:.2f} {'▲' if now >= pre else '▼'}"

    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {get_ma_info('5MA')}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {get_ma_info('10MA')}</span>
            <span style="color: #9C27B0;">20MA: {get_ma_info('20MA')}</span>
        </div>
    """, unsafe_allow_html=True)

    # 【繪圖】
    mc = mpf.make_marketcolors(up='red', down='green', edge='inherit', wick='inherit', volume='in')
    style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--')
    plots = [mpf.make_addplot(df[m], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])]
    
    fig, axlist = mpf.plot(df, type='candle', style=style, addplot=plots, returnfig=True, figsize=(10, 6), volume=True)
    ax = axlist[0]
    
    # 繪製轉折線與標記
    if len(zigzag_points) > 1:
        ax.plot(*zip(*zigzag_points), color='black', alpha=0.5, linewidth=1.5, zorder=3)
    for idx, row in df[df['Label'].notnull()].iterrows():
        is_h = row['Label'] == "H"
        ax.text(df.index.get_loc(idx), row['High' if is_h else 'Low'], row['Label'],
                color='red' if is_h else 'green', weight='bold', ha='center',
                bbox=dict(boxstyle="circle,pad=0.1", fc="yellow", ec="none", alpha=0.6))
    
    st.pyplot(fig)
