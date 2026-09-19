import pandas as pd
from FinMind.data import DataLoader

# 初始化 FinMind
dl = DataLoader()

def get_chip_data(start_date: str):
    print("正在下載三大法人資料...")
    df_institutional = dl.taiwan_stock_institutional_investors(
        start_date=start_date
    )
    return df_institutional

def filter_stocks():
    start_date = "2026-08-01" 
    df = get_chip_data(start_date)
    
    if df.empty:
        print("無法取得資料，請檢查網路或 API 限制。")
        return

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
    print(f"符合 5、10、15 日外資投信同買的股票清單（截至 {latest_date}）：")
    print(results[['stock_id', 'Foreign_Sum_5', 'Foreign_Sum_10', 'Foreign_Sum_15', 
                   'Investment_Trust_Sum_5', 'Investment_Trust_Sum_10', 'Investment_Trust_Sum_15']])

if __name__ == "__main__":
    filter_stocks()
