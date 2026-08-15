import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from config import WIDE_TABLE_PATH
from utils.batch_factor_test import BatchFactorEvaluator, FactorOrthogonalizer

def run_orthogonalization_comparison():
    df = pd.read_parquet(WIDE_TABLE_PATH) 
    
    target_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe']
    factor_cols = [col for col in target_factors if col in df.columns and not df[col].isna().all()]

    reversal_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d']
    for col in reversal_factors:
        if col in factor_cols:
            df[col] = df[col] * -1

    MIN_STOCKS = 30
    evaluator = BatchFactorEvaluator(friction_cost=0.003, min_stocks=MIN_STOCKS)
    orthogonalizer = FactorOrthogonalizer(min_stocks=MIN_STOCKS)

    df_preprocessed = evaluator.preprocess_cross_section(df, factor_cols)
    
    # 计算截面相关性矩阵均值
    corr_before = df_preprocessed.groupby('date')[factor_cols].corr().groupby(level=1).mean()
    print("\n>>> 正交化前因子相关性矩阵 (Pearson):")
    print(corr_before.round(4).to_markdown())

    results_before = evaluator.run_batch_evaluation(df_preprocessed, factor_cols)
    print(results_before.to_markdown())

    df_orth = orthogonalizer.process(df_preprocessed, factor_cols)
    # 正交化后再次标准化归一化量纲
    df_ready = evaluator.preprocess_cross_section(df_orth, factor_cols)
    
    # 计算正交化后的截面相关性矩阵均值
    corr_after = df_ready.groupby('date')[factor_cols].corr().groupby(level=1).mean()
    print("\n正交化后因子相关性矩阵")
    print(corr_after.round(4).to_markdown())

    print("\n正交化后因子表现评估")
    results_after = evaluator.run_batch_evaluation(df_ready, factor_cols)
    print(results_after.to_markdown())

if __name__ == '__main__':
    run_orthogonalization_comparison()