import streamlit as st
import pandas as pd
from FinMind.data import DataLoader

# 網頁標題
st.title("台股外資、投信同買篩選器")

# 初始化 FinMind
@st.cache_resource
def get_dataloader():
    return DataLoader()

dl = get_dataloader()

@st.cache_data
def get_chip_data(start_date: str):
    df_institutional = dl.taiwan_stock_institutional_investors(
        start_date=start_date
    )
    return df_institutional

# 建立按鈕讓使用者手動點擊執行（避免每次開網頁自動重抓被限流）
if st.button("開始篩選 5、10、15 日法人同買股票"):
    with st.spinner("正在下載三大法人資料並計算中，請稍候..."):
        start_date = "2026-08-01" 
        df = get_chip_data(start_date)
        
        if df.empty:
            st.warning("無法取得資料，請檢查網路或 API 限制。")
        else:
            institutions = ['Foreign_Investor', 'Investment_Trust']
            df_filtered = df[df['name'].isin(institutions)].copy()
            
            df_filtered['net'] = df_filtered['buy'] - df_filtered['sell']
            
            pivot_df = df_filtered.pivot_table(
                index=['date', 'stock_id'], 
                columns='name', 
                values='net', 
                aggfunc='sum'
            ).reset_index()
            
            for col in ['Foreign_Investor', 'Investment_Trust']:
                if col not in pivot_df.columns:
                    pivot_df[col] = 0

            pivot_df = pivot_df.sort_values(['stock_id', 'date'])
            
            for days in [5, 10, 15]:
                pivot_df[f'Foreign_Sum_{days}'] = pivot_df.groupby('stock_id']['Foreign_Investor'].rolling(days, min_periods=days).sum().reset_index(0, drop=True)
                pivot_df[f'Investment_Trust_Sum_{days}'] = pivot_df.groupby('stock_id']['Investment_Trust'].rolling(days, min_periods=days).sum().reset_index(0, drop=True)

            latest_date = pivot_df['date'].max()
            latest_data = pivot_df[pivot_df['date'] == latest_date]
            
            condition = (
                (latest_data['Foreign_Sum_5'] > 0) & 
                (latest_data['Foreign_Sum_10'] > 0) & 
                (latest_data['Foreign_Sum_15'] > 0) &
                (latest_data['Investment_Trust_Sum_5'] > 0) & 
                (latest_data['Investment_Trust_Sum_10'] > 0) & 
                (latest_data['Investment_Trust_Sum_15'] > 0)
            )
            
            results = latest_data[condition]
            
            st.success(f"篩選完成！截至日期：{latest_date}")
            st.write(f"符合 5、10、15 日外資與投信皆買超的股票共 {len(results)} 檔：")
            
            # 在網頁上呈現互動式表格
            st.dataframe(results[['stock_id', 'Foreign_Sum_5', 'Foreign_Sum_10', 'Foreign_Sum_15', 
                                  'Investment_Trust_Sum_5', 'Investment_Trust_Sum_10', 'Investment_Trust_Sum_15']])
