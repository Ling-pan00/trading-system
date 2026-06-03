import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf
import numpy as np
import twstock



    # 轉折圖
    st.write("---")
    st.subheader("🎯 轉折監測器")
    pool_all = pd.concat([st.session_state[k] for k in pools.values() if not st.session_state[k].empty]).drop_duplicates(subset=['ticker'])
    sel = st.selectbox("分析個股：", pool_all["代號"].tolist())
    ticker = pool_all[pool_all["代號"] == sel]["ticker"].values[0]
    
    df_k = yf.download(ticker, period="3mo", progress=False)
    if isinstance(df_k.columns, pd.MultiIndex): df_k.columns = df_k.columns.get_level_values(0)
    df_k['5MA'], df_k['10MA'], df_k['20MA'] = df_k['Close'].rolling(5).mean(), df_k['Close'].rolling(10).mean(), df_k['Close'].rolling(20).mean()
    
    # HTML 美觀看板
    l, p = df_k.iloc[-1], df_k.iloc[-2]
    st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #6c757d; font-family: monospace; font-size: 16px; font-weight: bold;">
            <span style="color: #FF9800; margin-right: 20px;">5MA: {l['5MA']:.2f} {'▲' if l['5MA'] > p['5MA'] else '▼'}</span>
            <span style="color: #2196F3; margin-right: 20px;">10MA: {l['10MA']:.2f} {'▲' if l['10MA'] > p['10MA'] else '▼'}</span>
            <span style="color: #9C27B0;">20MA: {l['20MA']:.2f} {'▲' if l['20MA'] > p['20MA'] else '▼'}</span>
        </div>
    """, unsafe_allow_html=True)
    
    # 繪圖
    fig, axlist = mpf.plot(df_k.iloc[-90:], type='candle', returnfig=True, volume=True, figsize=(10, 6), 
                           addplot=[mpf.make_addplot(df_k[m].iloc[-90:], color=c) for m, c in zip(['5MA','10MA','20MA'], ['orange','blue','purple'])])
    ax = axlist[0]
    for idx, val, lbl in get_zigzag_points(df_k):
        if idx in df_k.iloc[-90:].index:
            ax.annotate(lbl, (df_k.index.get_loc(idx), val), ha='center', color='red' if lbl=='H' else 'green', weight='bold', bbox=dict(fc="yellow", alpha=0.5))
    st.pyplot(fig)


