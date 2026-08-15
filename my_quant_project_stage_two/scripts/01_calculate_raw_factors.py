"""
Script 01: 底层全量基础因子计算
读取原始行情与财务数据，调用 FactorCalculator 计算技术面、基本面与另类衍生因子
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import RAW_DATA_DIR, PROCESSED_DATA_DIR
from src.factor_calculator import FactorCalculator


def main():

    price_file = RAW_DATA_DIR / "daily_price.parquet"
    fin_file = RAW_DATA_DIR / "financial_data.parquet"

    if not price_file.exists():
        dates = pd.date_range('2023-01-01', '2023-06-30', freq='B')
        codes = ['000001', '600000', '300059']
        idx = pd.MultiIndex.from_product([dates, codes], names=['date', 'code'])
        df_price = pd.DataFrame(index=idx).reset_index()
        df_price['close'] = np.random.uniform(10, 50, size=len(df_price))
        df_price['volume'] = np.random.uniform(1e5, 1e6, size=len(df_price))
        df_price['market_cap'] = np.random.uniform(50e8, 500e8, size=len(df_price))
        df_price['industry'] = np.random.choice(['Finance/LargeCap', 'Growth/Tech', 'Others'], size=len(df_price))
    else:
        df_price = pd.read_parquet(price_file)

    if not fin_file.exists():
        df_fin = pd.DataFrame({
            'code': ['000001', '600000', '300059'],
            'report_date': pd.to_datetime(['2023-03-31', '2023-03-31', '2023-03-31']),
            'net_profit': [10e8, 15e8, 2e8],
            'total_equity': [100e8, 150e8, 30e8],
            'total_assets': [500e8, 2000e8, 80e8],
            'total_liabilities': [400e8, 1850e8, 50e8],
            'operating_revenue': [30e8, 50e8, 10e8],
            'operating_cost': [20e8, 30e8, 5e8],
            'operating_cash_flow': [12e8, 10e8, 3e8]
        })
    else:
        df_fin = pd.read_parquet(fin_file)

    calculator = FactorCalculator()

    # 1. 计算技术面量价因子
    df_tech = calculator.calculate_technical_factors(df_price, price_col='close', vol_col='volume')

    df_combined = pd.merge(df_tech, df_fin, on='code', how='left')
    
    # 2. 计算基本面衍生因子
    df_fund = calculator.calculate_fundamental_factors(df_combined)
    
    # 3. 计算另类与宏观衍生因子
    df_raw_factors = calculator.calculate_alternative_factors(df_fund)

    # 4. 结果落盘
    out_path = PROCESSED_DATA_DIR / "step1_raw_factors.parquet"
    df_raw_factors.to_parquet(out_path, index=False)
    
    print(f"\n基础因子计算完成，总记录数: {len(df_raw_factors)}")
    print(f"结果已落盘至: {out_path}")

if __name__ == "__main__":
    main()