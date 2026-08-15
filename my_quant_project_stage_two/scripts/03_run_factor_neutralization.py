"""
Script 03: 因子特征去极值、标准化与中性化处理
横截面执行 MAD 去极值、Z-score 标准化与 OLS 行业/市值中性化
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import PROCESSED_DATA_DIR, FACTOR_CONFIG
from src import FactorNeutralizer


def main():

    in_path = PROCESSED_DATA_DIR / "step2_cleaned_factors.parquet"
    if not in_path.exists():
        print(f"找不到上游数据 {in_path}，请先执行 02 脚本")
        return

    df_cleaned = pd.read_parquet(in_path)
    
    mad_multiplier = FACTOR_CONFIG.get('mad_multiplier', 3.0)
    neutralizer = FactorNeutralizer(mad_multiplier=mad_multiplier)

    target_factors = ['mom_10d', 'mom_20d', 'volatility_20d', 'volume_mean_20d', 'roe', 'ep']
    factor_cols = [c for c in target_factors if c in df_cleaned.columns]

    # 1. 横截面 MAD 去极值 + Z-score 标准化
    df_std = neutralizer.process_standardization(df_cleaned, factor_cols)

    # 2. OLS 行业与市值中性化 (剥离风格 Beta)
    if 'market_cap' in df_std.columns and 'industry' in df_std.columns:
        df_neutral = neutralizer.neutralize_factors(
            df_std, 
            factor_cols=factor_cols, 
            size_col='market_cap', 
            industry_col='industry'
        )
    else:
        df_neutral = df_std

    out_path = PROCESSED_DATA_DIR / "step3_neutralized_factors.parquet"
    df_neutral.to_parquet(out_path, index=False)

    print(f"结果已落盘至: {out_path}")

if __name__ == "__main__":
    main()