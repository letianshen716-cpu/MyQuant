import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import ssl
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()
print("【系统状态】网络安全拦截补丁已就绪...")

import QUANTAXIS as QA
import pandas as pd
from config import FACTOR_STOCKS, FACTOR_START_DATE, FACTOR_END_DATE

def use_qa_data():
    print("从 MongoDB 拉取数据")
    
    multi_stock_data = QA.QA_fetch_stock_day_adv(
        FACTOR_STOCKS, 
        start=FACTOR_START_DATE, 
        end=FACTOR_END_DATE
    )
    
    if multi_stock_data is None:
        print("未查到数据")
        return

    print("\nDataStruct")
    df = multi_stock_data.data
    print("\n转化为 DataFrame")
    print(df.head())

    print("\n计算 MACD 指标")
    macd_df = multi_stock_data.add_func(QA.QA_indicator_MACD)
    print(macd_df.tail())

if __name__ == '__main__':
    use_qa_data()