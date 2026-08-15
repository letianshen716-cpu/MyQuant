"""
Script 02: 金融数据清洗与 PIT 时序严格对齐
处理缺失值、剔除异常，并防范财报前视偏差 (Look-ahead Bias)
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import PROCESSED_DATA_DIR
from src import DataCleaner


def main():

    in_path = PROCESSED_DATA_DIR / "step1_raw_factors.parquet"
    if not in_path.exists():
        print(f"找不到上游数据 {in_path}，请先执行 01_calculate_raw_factors.py")
        return
        
    df_raw = pd.read_parquet(in_path)
    cleaner = DataCleaner()

    df_price = df_raw.drop(columns=['net_profit', 'total_equity'], errors='ignore')

    df_fin = df_raw[['code', 'net_profit', 'total_equity']].drop_duplicates()
    df_fin['report_date'] = pd.to_datetime('2023-03-31') 

    df_aligned = cleaner.align_pit_financials(df_price, df_fin)

    target_factors = ['mom_10d', 'mom_20d', 'volatility_20d', 'volume_mean_20d', 'roe', 'ep']
    factor_cols = [c for c in target_factors if c in df_aligned.columns]
    
    df_cleaned = cleaner.fill_missing_with_industry_median(df_aligned, factor_cols, industry_col='industry')

    out_path = PROCESSED_DATA_DIR / "step2_cleaned_factors.parquet"
    df_cleaned.to_parquet(out_path, index=False)

    print(f"包含字段: {list(df_cleaned.columns)}")
    print(f"结果已落盘至: {out_path}")

if __name__ == "__main__":
    main()