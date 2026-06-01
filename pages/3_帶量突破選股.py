import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import pytz

# ==========================================
# 1. 頁面配置與股票池 (完整還原 530 檔)
# ==========================================
st.set_page_config(page_title="強勢帶量突破系統", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')
today_tw = datetime.now(tw_tz).date()

st.title("⚡ 策略四：強勢帶量突破選股系統")
st.caption(f"監控時間：{datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')} | 策略：20日新高 + 2倍增量 + ATR止損")

def get_industry_stock_pool():
    # 這是您提供的 530 檔完整列表
    full_pool = [
        "1503.TW", "1504.TW", "1513.TW", "1514.TW", "1519.TW", "1521.TW", "1522.TW", "1524.TW", "1525.TW", "1526.TW",
        "1527.TW", "1528.TW", "1529.TW", "1530.TW", "1531.TW", "1532.TW", "1533.TW", "1535.TW", "1536.TW", "1537.TW",
        "1538.TW", "1539.TW", "1540.TW", "1541.TW", "1560.TW", "1582.TW", "1583.TWO", "1584.TWO", "1586.TWO", "1587.TWO",
        "1591.TWO", "1593.TWO", "1597.TWO", "1599.TWO", "1605.TW", "1608.TW", "1704.TW", "1708.TW", "1710.TW", "1711.TW",
        "1712.TW", "1713.TW", "1714.TW", "1717.TW", "1718.TW", "1720.TW", "1721.TW", "1722.TW", "1723.TW", "1726.TW",
        "1727.TW", "1730.TW", "1731.TW", "1732.TW", "1733.TW", "1734.TW", "1735.TW", "1736.TW", "1742.TWO", "1750.TWO",
        "2302.TW", "2303.TW", "2329.TW", "2330.TW", "2337.TW", "2338.TW", "2344.TW", "2351.TW", "2363.TW", "2369.TW",
        "2379.TW", "2388.TW", "2408.TW", "2436.TW", "2441.TW", "2449.TW", "2454.TW", "2458.TW", "2481.TW", "3006.TW",
        "3016.TW", "3034.TW", "3035.TW", "3041.TW", "3054.TW", "3094.TWO", "3105.TWO", "3131.TWO", "3141.TWO", "3169.TWO",
        "3189.TW", "3227.TWO", "3228.TWO", "3260.TWO", "3264.TWO", "3265.TWO", "3289.TWO", "3374.TWO", "3413.TW", "3438.TWO",
        "3443.TW", "3527.TWO", "3529.TWO", "3532.TW", "3545.TW", "3556.TWO", "3567.TWO", "3583.TW", "3587.TWO", "3588.TWO",
        "3592.TWO", "3653.TW", "3661.TW", "3675.TWO", "3680.TWO", "3686.TW", "3707.TWO", "3711.TW", "4919.TW", "4952.TW",
        "4961.TW", "4966.TWO", "4967.TW", "4968.TW", "4976.TW", "5269.TW", "5274.TWO", "5285.TW", "5289.TWO", "5305.TW",
        "5347.TWO", "5351.TWO", "5425.TWO", "5471.TWO", "5483.TWO", "6104.TWO", "6125.TWO", "6129.TWO", "6138.TWO", "6147.TWO",
        "6182.TWO", "6202.TW", "6224.TW", "6239.TW", "6243.TW", "6257.TW", "6271.TW", "6287.TWO", "6411.TWO", "6415.TW",
        "6435.TWO", "6451.TW", "6462.TWO", "6488.TWO", "6494.TWO", "6510.TWO", "6526.TW", "6531.TW", "6533.TW", "6548.TWO",
        "6568.TWO", "6573.TWO", "6679.TWO", "6684.TWO", "6719.TW", "6732.TWO", "6756.TW", "6770.TW", "6789.TW", "6806.TW",
        "6834.TWO", "8016.TW", "8028.TWO", "8054.TWO", "8081.TWO", "8110.TW", "8131.TW", "8150.TW", "8261.TW", "8271.TW",
        "2324.TW", "2331.TW", "2352.TW", "2353.TW", "2356.TW", "2357.TW", "2362.TW", "2364.TW", "2365.TW", "2376.TW",
        "2377.TW", "2382.TW", "2395.TW", "2397.TW", "2399.TW", "2405.TW", "2424.TW", "2495.TW", "3005.TW", "3013.TW",
        "3017.TW", "3022.TW", "3046.TW", "3057.TW", "3231.TW", "3325.TWO", "3356.TW", "3416.TW", "3494.TW", "3515.TW",
        "3540.TWO", "3563.TW", "3570.TWO", "3615.TWO", "3694.TW", "3706.TW", "4916.TW", "4938.TW", "5215.TW", "5410.TWO",
        "6121.TWO", "6143.TWO", "6150.TWO", "6160.TWO", "6206.TW", "6230.TW", "6235.TW", "6277.TW", "6412.TW", "6414.TW",
        "6491.TW", "6509.TWO", "6561.TWO", "6613.TWO", "6625.TW", "6641.TW", "6695.TW", "6698.TW", "6811.TWO", "8032.TWO",
        "8040.TWO", "8050.TWO", "8064.TWO", "8076.TWO", "8114.TW", "8124.TWO", "8163.TW", "8210.TW", "8477.TWO", "2317.TW",
        "2354.TW", "2355.TW", "2359.TW", "2360.TW", "2383.TW", "2423.TW", "2461.TW", "2464.TW", "2474.TW", "2482.TW",
        "2491.TWO", "3023.TW", "3030.TW", "3138.TW", "3209.TW", "3211.TWO", "3288.TWO", "3312.TW", "3406.TW", "3548.TWO",
        "3550.TW", "3580.TWO", "3596.TW", "3622.TW", "3645.TW", "3669.TW", "4541.TWO", "4551.TWO", "4906.TW", "5225.TW",
        "5443.TWO", "5490.TWO", "6115.TW", "6139.TW", "6153.TW", "6176.TW", "6184.TWO", "6205.TW", "6213.TW", "6220.TWO",
        "2340.TW", "2349.TW", "2374.TW", "2393.TW", "2406.TW", "2409.TW", "2426.TW", "2438.TW", "2448.TWO", "2489.TW",
        "3008.TW", "3019.TW", "3031.TW", "3038.TW", "3049.TW", "3050.TW", "3051.TW", "3059.TW", "3338.TW", "3359.TWO",
        "3362.TWO", "3363.TWO", "3383.TWO", "3437.TW", "3450.TW", "3454.TW", "3481.TW", "3504.TW", "3519.TW", "3523.TWO",
        "3535.TW", "3557.TW", "3562.TWO", "3576.TW", "3591.TW", "3623.TWO", "3624.TWO", "3630.TWO", "3666.TW", "3673.TW",
        "3679.TW", "3685.TWO", "4205.TWO", "4934.TW", "4944.TWO", "4956.TW", "4960.TW", "4972.TW", "4976.TW", "5234.TW",
        "5259.TWO", "5371.TWO", "5386.TWO", "5432.TWO", "6116.TW", "6120.TW", "6164.TW", "6168.TW", "6171.TWO", "6226.TW",
        "2314.TW", "2321.TW", "2332.TW", "2345.TW", "2412.TW", "2419.TW", "2439.TW", "2444.TW", "2450.TW", "2455.TW",
        "2485.TW", "2496.TWO", "2498.TW", "3025.TW", "3027.TW", "3032.TW", "3045.TW", "3047.TW", "3062.TW", "3092.TW",
        "3152.TWO", "3163.TWO", "3217.TWO", "3234.TWO", "3305.TW", "3314.TWO", "3321.TWO", "3363.TWO", "3380.TW", "3419.TW",
        "3491.TWO", "3546.TWO", "3558.TWO", "3596.TW", "3665.TW", "3672.TWO", "3682.TW", "3694.TW", "4903.TWO", "4904.TW",
        "4905.TWO", "4906.TW", "4908.TWO", "4909.TWO", "4916.TW", "4977.TW", "4979.TWO", "5314.TWO", "5321.TWO", "5353.TWO",
        "5452.TWO", "5465.TWO", "6136.TW", "6142.TW", "6152.TW", "6190.TWO", "6216.TW", "6218.TWO", "6241.TWO", "6245.TWO",
        "2308.TW", "2313.TW", "2316.TW", "2327.TW", "2328.TW", "2355.TW", "2367.TW", "2368.TW", "2375.TW", "2383.TW",
        "2385.TW", "2392.TW", "2402.TW", "2413.TW", "2415.TW", "2420.TW", "2421.TW", "2428.TW", "2429.TW", "2431.TW",
        "2440.TW", "2457.TW", "2460.TW", "2462.TW", "2465.TW", "2467.TW", "2472.TW", "2476.TW", "2478.TW", "2483.TW",
        "2484.TW", "2492.TW", "2493.TW", "3003.TW", "3010.TW", "3011.TW", "3015.TW", "3026.TW", "3029.TW", "3033.TW",
        "3037.TW", "3042.TW", "3043.TW", "3058.TW", "3090.TW", "3202.TWO", "3211.TWO", "3218.TWO", "3221.TWO", "3232.TWO",
        "3236.TWO", "3241.TWO", "3290.TWO", "3303.TWO", "3315.TW", "3317.TWO", "3323.TWO", "3324.TWO", "3332.TWO", "3339.TWO",
        "3356.TW", "3360.TWO", "3368.TW", "3376.TW", "3428.TWO", "3432.TW", "3466.TWO", "3468.TWO", "3484.TWO", "3489.TWO",
        "3492.TWO", "3508.TWO", "3520.TWO", "3526.TWO", "3528.TWO", "3531.TWO", "3533.TW", "3540.TWO", "3552.TWO", "3564.TWO",
        "3581.TWO", "3607.TW", "3609.TWO", "3624.TWO", "3628.TWO", "3631.TWO", "3632.TW", "3672.TWO", "4534.TWO", "4542.TWO",
        "4915.TW", "4927.TW", "4943.TW", "4947.TWO", "4953.TWO", "4958.TW", "4965.TWO", "4971.TWO", "4987.TWO", "4989.TW",
        "2347.TW", "2414.TW", "2430.TW", "2459.TW", "3014.TW", "3036.TW", "3048.TW", "3055.TW", "3207.TWO", "3232.TWO",
        "3318.TW", "3518.TW", "3702.TW", "5434.TW", "6118.TWO", "6148.TWO", "6154.TWO", "6189.TW", "6212.TW", "6234.TWO",
        "6265.TWO", "6281.TW", "8033.TW", "8042.TWO", "8068.TWO", "8096.TWO", "8112.TW", "8240.TWO", "8255.TWO", "8277.TWO",
        "2425.TW", "2427.TW", "2453.TW", "2468.TW", "2471.TW", "2480.TW", "3021.TW", "3029.TW", "3040.TW", "3130.TWO",
        "3546.TWO", "4953.TWO", "4994.TW", "5203.TWO", "5209.TWO", "5210.TWO", "5310.TWO", "5403.TWO", "5478.TWO", "6112.TW",
        "6140.TWO", "6148.TWO", "6169.TWO", "6180.TWO", "6214.TW", "6221.TWO", "6231.TWO", "6240.TWO", "6417.TWO", "6493.TWO",
        "6516.TWO", "6549.TWO", "6590.TWO", "6683.TWO", "6690.TW", "6811.TWO", "8044.TWO", "8171.TWO", "8249.TW", "8416.TWO",
        "6696.TWO", "6830.TWO", "6963.TW", "8454.TW"
    ]
    return sorted(list(set(full_pool)))

# ==========================================
# 2. 掃描核心運算
# ==========================================
total_pool = get_industry_stock_pool()
st.write(f"📊 **帶量突破雷達範圍**：共有 {len(total_pool)} 檔核心標的。")

if st.button("⚡ 啟動掃描", type="primary"):
    start_dt = (today_tw - timedelta(days=60)).strftime("%Y-%m-%d")
    end_dt = (today_tw + timedelta(days=1)).strftime("%Y-%m-%d")
    
    progress_bar = st.progress(0)
    results = []
    
    with st.spinner("🚀 正在運算量價與風險模型..."):
        df_raw = yf.download(tickers=total_pool, start=start_dt, end=end_dt, auto_adjust=True, group_by='ticker', progress=False)
        
        for idx, s_id in enumerate(total_pool):
            progress_bar.progress((idx + 1) / len(total_pool))
            
            df = df_raw[s_id] if isinstance(df_raw.columns, pd.MultiIndex) else df_raw
            if len(df) < 22: continue
            
            # 策略指標計算
            df['TR'] = abs(df['High'] - df['Low'])
            df['ATR'] = df['TR'].rolling(window=10).mean()
            
            last_close = df['Close'].iloc[-1]
            high_20 = df['Close'].iloc[-21:-1].max()
            vol_avg_20 = df['Volume'].iloc[-21:-1].mean()
            current_vol = df['Volume'].iloc[-1]
            current_atr = df['ATR'].iloc[-1]
            
            # 策略篩選：突破20日新高 + 今日成交量大於20日均量2倍
            if last_close > high_20 and current_vol > (vol_avg_20 * 2):
                entry_price = round(float(last_close), 2)
                # 止損設定：收盤價 - 1.5 倍 ATR
                stop_loss = round(entry_price - (current_atr * 1.5), 2)
                
                results.append({
                    "代碼": s_id, 
                    "建議進場價": entry_price, 
                    "ATR止損價": stop_loss,
                    "波動強度": round(current_atr, 2)
                })
                
    if results:
        st.success(f"掃描完成！發現 {len(results)} 檔標的。")
        st.table(pd.DataFrame(results))
    else:
        st.info("今日無標的完全符合強勢突破條件。")
