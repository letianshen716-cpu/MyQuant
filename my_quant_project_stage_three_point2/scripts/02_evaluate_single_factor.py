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

    target_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe']

    factor_cols = [col for col in target_factors if col in df.columns and not df[col].isna().all()]
    
    if not factor_cols:
        return
        
    print(f"实际参与本次评估的因子有: {factor_cols}")
    
    # 实例化工具箱
    evaluator = BatchFactorEvaluator(friction_cost=0.003, min_stocks=3) 
    orthogonalizer = FactorOrthogonalizer(min_stocks=3)
    
    print("\n>>> 2. 预处理：截面 MAD去极值 + Z-score标准化")
    df_standardized = evaluator.preprocess_cross_section(df, factor_cols)
    
    print("\n>>> 3. 正交化：剔除共线性干扰 (Symmetric Orthogonalization)")
    df_orth = orthogonalizer.process(df_standardized, factor_cols)
    # 正交化后建议再次标准化归一化量纲
    df_ready = evaluator.preprocess_cross_section(df_orth, factor_cols)
    
    print("\n>>> 4. 统计学习特征筛选：Lasso 惩罚回归")
    core_factors = StatisticalSelector.select_factors(df_ready, factor_cols)
    
    if not core_factors:
        print("未筛选出有效因子，退出评估。")
        return

    print("\n>>> 5. 核心因子批量显著性及分组检验")
    results = evaluator.run_batch_evaluation(df_ready, core_factors)
    print(results.to_markdown())
    
    print("\n>>> 6. 核心因子异质性研究 (市场环境与行业板块)")
    top_factor = core_factors[0] # 取出第一核心因子
    
    print(f"\n【{top_factor}】在不同市场状态 (Market State) 下的表现:")
    market_stats = HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'market_state')
    print(market_stats.to_markdown())
    
    print(f"\n【{top_factor}】在不同行业板块 (Industry) 下的表现:")
    industry_stats = HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'industry')
    print(industry_stats.to_markdown())

if __name__ == '__main__':
    run_advanced_evaluation()