"""
Script 01: 历史底层量价因子滚动提取
分年份流式抽取日线行情，利用跨年缓冲窗口计算基础动量并落盘
"""

import gc
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pymongo
from config.settings import FACTOR_ALL_HISTORY_PATH, MONGO_URI


def generate_history_factors():
    client = pymongo.MongoClient(MONGO_URI)
    collection = client['quantaxis']['stock_day']

    first_record = collection.find_one(sort=[("date", 1)])
    last_record = collection.find_one(sort=[("date", -1)])

    if not first_record or not last_record:
        return

    start_year = int(first_record['date'][:4])
    end_year = int(last_record['date'][:4])
    print(f"数据库时间跨度: {first_record['date']} 至 {last_record['date']}")

    # 若已存在旧的 CSV 文件则清理
    if os.path.exists(FACTOR_ALL_HISTORY_PATH):
        os.remove(FACTOR_ALL_HISTORY_PATH)

    total_rows = 0

    # 分年处理，防止内存溢出
    for year in range(start_year, end_year + 1):
        print(f"\n [{year}] 年的量价数据")
        buffer_start_date = f"{year - 1}-11-15"
        current_year_end = f"{year}-12-31"

        cursor = collection.find(
            {'date': {'$gte': buffer_start_date, '$lte': current_year_end}},
            {'_id': 0, 'date': 1, 'code': 1, 'close': 1}
        )
        df_raw = pd.DataFrame(list(cursor))
        if df_raw.empty:
            continue

        df_raw['date'] = pd.to_datetime(df_raw['date'])
        df_raw['close'] = df_raw['close'].astype(float)
        df_raw['code'] = df_raw['code'].astype(str).str.zfill(6)
        df_raw = df_raw.sort_values(by=['code', 'date']).reset_index(drop=True)

        df_raw['mom_10'] = df_raw.groupby('code')['close'].pct_change(periods=10)
        df_raw['mom_20'] = df_raw.groupby('code')['close'].pct_change(periods=20)

        df_factor = df_raw[['date', 'code', 'mom_10', 'mom_20']].dropna()
        df_factor = df_factor[df_factor['date'] >= pd.to_datetime(f"{year}-01-01")]

        valid_rows = len(df_factor)
        total_rows += valid_rows

        write_header = not os.path.exists(FACTOR_ALL_HISTORY_PATH)
        df_factor.to_csv(
            FACTOR_ALL_HISTORY_PATH,
            mode='a',
            index=False,
            header=write_header,
            encoding='utf-8-sig'
        )

        del df_raw, df_factor
        gc.collect()

    print(f"\n全量历史因子抽取完毕。总计 {total_rows} 行，保存至 {FACTOR_ALL_HISTORY_PATH}")


if __name__ == '__main__':
    generate_history_factors()