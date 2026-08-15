import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import ssl
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import pandas as pd
from config import WIDE_TABLE_PATH
from utils.batch_factor_test import (
    BatchFactorEvaluator, 
    FactorOrthogonalizer, 
    StatisticalSelector, 
    HeterogeneityAnalyzer
)

def run_advanced_evaluation():
    df = pd.read_parquet(WIDE_TABLE_PATH)
    print(df.groupby('industry')['code'].nunique())
    
    target_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe']
    
    factor_cols = [col for col in target_factors if col in df.columns and not df[col].isna().all()]
    
    if not factor_cols:
        return
        
    print(f"实际参与本次评估的因子有: {factor_cols}")
    
    reversal_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d']
    print("\n 侦测到反转因子，正在乘以 -1 将其转化为正向 Alpha 因子")
    for col in reversal_factors:
        if col in factor_cols:
            df[col] = df[col] * -1

    MIN_STOCKS = 30
    evaluator = BatchFactorEvaluator(friction_cost=0.003, min_stocks=MIN_STOCKS) 
    orthogonalizer = FactorOrthogonalizer(min_stocks=MIN_STOCKS)
    
    print("\n 截面 MAD去极值 + Z-score标准化")
    df_standardized = evaluator.preprocess_cross_section(df, factor_cols)
    
    print("\n 剔除共线性干扰")
    df_orth = orthogonalizer.process(df_standardized, factor_cols)
    
    df_ready = evaluator.preprocess_cross_section(df_orth, factor_cols)
    
    print("\n统计学习特征筛选：Lasso 惩罚回归")
    core_factors = StatisticalSelector.select_factors(df_ready, factor_cols)
    
    if not core_factors:
        print("未筛选出有效因子，退出评估。")
        return

    print("\n核心因子批量显著性及分组检验")
    results = evaluator.run_batch_evaluation(df_ready, core_factors)
    print(results.to_markdown())
    
    print("\n核心因子异质性研究 (市场环境与行业板块)")
    top_factor = core_factors[0] 
    
    print(f"\n【{top_factor}】在不同市场状态 (Market State) 下的表现:")
    market_stats = HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'market_state')
    print(market_stats.to_markdown())
    
    print(f"\n【{top_factor}】在不同行业板块 (Industry) 下的表现:")
    industry_stats = HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'industry')
    print(industry_stats.to_markdown())

if __name__ == '__main__':
    run_advanced_evaluation()