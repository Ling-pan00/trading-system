import pandas as pd
from FinMind.data import DataLoader

# 初始化 FinMind
dl = DataLoader()

# 若有 FinMind Token 可在此登入（免費版可不填，但有流量限制）
# dl.login(user_id="your_user_id", password="your_password")

def get_chip_data(start_date: str):
    # 取得三大法人買賣超資料
    print("正在下載三大法人資料...")
    df_institutional = dl.taiwan_stock_institutional_investors(
        start_date=start_date
    )
    return df_institutional

# 篩選函式範例
def filter_stocks():
    # 設定回溯日期（例如抓取最近 3 個月以確保能計算 15 日數據）
    start_date = "2026-08-01" 
    df = get_chip_data(start_date)
    
    if df.empty:
        print("無法取得資料，請檢查網路或 API 限制。")
        return

    # 欄位整理：stock_id, date, name (外資/投信/自營商), buy, sell
    # 這裡以外資 (Foreign_Investor)、投信 (Investment_Trust) 為例
    # 將資料轉換為寬表格以便計算移動加總
    
    # 篩選出需要的法人別
    # FinMind 的 name 常見如: 'Foreign_Investor', 'Investment_Trust'
    institutions = ['Foreign_Investor', 'Investment_Trust']
    df_filtered = df[df['name'].isin(institutions)].copy()
    
    # 計算買賣超淨額 (buy - sell)
    df_filtered['net'] = df_filtered['buy'] - df_filtered['sell']
    
    # 透視表：股票代號、日期對應各法人淨買超
    pivot_df = df_filtered.pivot_table(
        index=['date', 'stock_id'], 
        columns='name', 
        values='net', 
        aggfunc='sum'
    ).reset_index()
    
    pivot_df = pivot_df.sort_values(['stock_id', 'date'])
    
    # 計算 5日、10日、15日滾動加總 (Rolling Sum)
    # 依 stock_id 分組計算 rolling
    for days in [5, 10, 15]:
        pivot_df[f'Foreign_Sum_{days}'] = pivot_df.groupby('stock_id']['Foreign_Investor'].rolling(days, min_periods=days).sum().reset_index(0, drop=True)
        pivot_df[f'Foreign_Sum_{days}'] = pivot_df.groupby('stock_id']['Investment_Trust'].rolling(days, min_periods=days).sum().reset_index(0, drop=True)

    # 取最新一個交易日來檢查
    latest_date = pivot_df['date'].max()
    latest_data = pivot_df[pivot_df['date'] == latest_date]
    
    # 篩選 5、10、15 日外資與投信皆為正數的股票
    # （若要把「主力」加入，可透過計算買賣超張數或特定主力券商集保戶股權分散表來定義）
    condition = (
        (latest_data['Foreign_Sum_5'] > 0) & (latest_data['Foreign_Sum_10'] > 0) & (latest_data['Foreign_Sum_15'] > 0) &
        (latest_data['Foreign_Sum_5'] > 0) & (latest_data['Foreign_Sum_10'] > 0) & (latest_data['Foreign_Sum_15'] > 0)
    )
    
    results = latest_data[condition]
    print(f"符合 5、10、15 日外資投信同買的股票清單（截至 {latest_date}）：")
    print(results[['stock_id', 'Foreign_Sum_5', 'Foreign_Sum_10', 'Foreign_Sum_15']])

if __name__ == "__main__":
    filter_stocks()
