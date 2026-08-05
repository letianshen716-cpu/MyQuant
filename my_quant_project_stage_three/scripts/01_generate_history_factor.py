import sys
from pathlib import Path

# 将阶段三根目录加入 PATH
sys.path.append(str(Path(__file__).parent.parent))

import os
import pymongo
import pandas as pd
import gc
from config import MONGO_URI, FACTOR_ALL_HISTORY_PATH

def auto_extract_all_data():
    print("【1】正在连接数据库，侦测数据总时间跨度...")
    client = pymongo.MongoClient(MONGO_URI)
    collection = client['quantaxis']['stock_day']
    
    first_record = collection.find_one(sort=[("date", 1)])
    last_record = collection.find_one(sort=[("date", -1)])
    
    if not first_record or not last_record:
        print("数据库是空的！")
        return
        
    start_year = int(first_record['date'][:4])
    end_year = int(last_record['date'][:4])
    
    print(f"数据库时间跨度: {first_record['date']} 至 {last_record['date']}")
    
    if os.path.exists(FACTOR_ALL_HISTORY_PATH):
        os.remove(FACTOR_ALL_HISTORY_PATH)
        
    total_rows = 0

    for year in range(start_year, end_year + 1):
        print(f"\n正在处理 [{year}] 年的全量数据")
        
        # 前置 45 天缓冲期防止因子计算断层
        buffer_start_date = f"{year - 1}-11-15"
        current_year_end = f"{year}-12-31"
        
        query = {'date': {'$gte': buffer_start_date, '$lte': current_year_end}}
        cursor = collection.find(query, {'_id': 0, 'date': 1, 'code': 1, 'close': 1})
        df_raw = pd.DataFrame(list(cursor))
        
        if df_raw.empty:
            continue
            
        df_raw['date'] = pd.to_datetime(df_raw['date'])
        df_raw['close'] = df_raw['close'].astype(float)
        df_raw = df_raw.sort_values(by=['code', 'date']).reset_index(drop=True)
        
        # 计算 20 日动量因子
        df_raw['factor_value'] = df_raw.groupby('code')['close'].pct_change(periods=20)
        
        # 裁剪出当年的数据
        df_factor = df_raw[['date', 'code', 'factor_value']].dropna()
        target_start_date = pd.to_datetime(f"{year}-01-01")
        df_factor = df_factor[df_factor['date'] >= target_start_date]
        
        valid_rows = len(df_factor)
        total_rows += valid_rows
        print(f"  -> 本年度有效因子共 {valid_rows} 行。")
        
        # 追加写入 CSV (动态使用 config 路径)
        write_header = not os.path.exists(FACTOR_ALL_HISTORY_PATH)
        df_factor.to_csv(FACTOR_ALL_HISTORY_PATH, mode='a', index=False, header=write_header, encoding='utf-8-sig')
        
        del df_raw, df_factor
        gc.collect()

    print(f"总计 {total_rows} 行，已落盘至: {FACTOR_ALL_HISTORY_PATH}")

if __name__ == '__main__':
    auto_extract_all_data()