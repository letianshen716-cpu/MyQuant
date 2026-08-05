import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pymongo
import pandas as pd
from config import MONGO_URI, FACTOR_STOCKS, FACTOR_START_DATE, FACTOR_END_DATE

def fetch_data_from_mongo(stock_codes: list, start_date: str, end_date: str) -> pd.DataFrame:
    print(f"正在连接本地 MongoDB 获取 {len(stock_codes)} 只股票的数据")
    
    client = pymongo.MongoClient(MONGO_URI)
    db = client['quantaxis']
    collection = db['stock_day']
    
    query = {
        'code': {'$in': stock_codes},
        'date': {'$gte': start_date, '$lte': end_date}
    }
    
    projection = {'_id': 0}
    cursor = collection.find(query, projection)
    df = pd.DataFrame(list(cursor))
    
    if df.empty:
        print("未查询到数据。")
        return df
        
    df['date'] = pd.to_datetime(df['date'])
    numeric_cols = ['open', 'high', 'low', 'close', 'vol', 'amount']
    df[numeric_cols] = df[numeric_cols].astype(float)
    
    df = df.sort_values(by=['date', 'code']).reset_index(drop=True)
    print("数据读取并清洗完毕")
    return df

if __name__ == '__main__':
    df_market_data = fetch_data_from_mongo(
        stock_codes=FACTOR_STOCKS,
        start_date=FACTOR_START_DATE,
        end_date=FACTOR_END_DATE
    )
    print("\n读取的 Pandas DataFrame")
    print(df_market_data.head())