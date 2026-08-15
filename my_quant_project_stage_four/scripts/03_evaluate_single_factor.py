"""
Script 03: 单因子批量检验、正交化与异质性分析
执行单因子 Alpha 实证检验、对称正交化、Lasso 特征降维及市场状态/行业异质性切片
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config.settings import BACKTEST_CONFIG, WIDE_TABLE_PATH
from src.factor_evaluator import FactorEvaluator
from src.factor_orthogonalizer import FactorOrthogonalizer
from src.heterogeneity_analyzer import HeterogeneityAnalyzer
from src.statistical_selector import StatisticalSelector


def run_advanced_evaluation():

    if not WIDE_TABLE_PATH.exists():
        return

    df = pd.read_parquet(WIDE_TABLE_PATH)
    print(df.groupby('industry')['code'].nunique())

    target_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe']
    factor_cols = [col for col in target_factors if col in df.columns and not df[col].isna().all()]

    if not factor_cols:
        return

    print(f"本次评估的因子有: {factor_cols}")

    reversal_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d']
    print("\n侦测到反转因子，正在乘以 -1 将其转化为正向 Alpha 因子")
    for col in reversal_factors:
        if col in factor_cols:
            df[col] = df[col] * -1.0

    min_stocks = BACKTEST_CONFIG.get('min_stocks_per_cross', 30)
    friction = BACKTEST_CONFIG.get('friction_cost', 0.003)

    evaluator = FactorEvaluator(friction_cost=friction, min_stocks=min_stocks)
    orthogonalizer = FactorOrthogonalizer(min_stocks=min_stocks)

    # 预处理：截面 MAD 去极值 + Z-score 标准化
    print("\n预处理：截面 MAD去极值 + Z-score 标准化")
    df_standardized = evaluator.preprocess_cross_section(df, factor_cols)

    # 对称正交化：剔除共线性干扰
    print("\n正交化：剔除共线性干扰 (Symmetric Orthogonalization)")
    df_orth = orthogonalizer.process(df_standardized, factor_cols)
    df_ready = evaluator.preprocess_cross_section(df_orth, factor_cols)

    # 统计学习特征筛选：Lasso 惩罚回归
    print("\n统计学习特征筛选：Lasso 惩罚回归")
    core_factors = StatisticalSelector.select_factors(df_ready, factor_cols)

    if not core_factors:
        return

    # 核心因子批量显著性与分组检验
    print("\n核心因子批量显著性及分组检验")
    results = evaluator.run_batch_evaluation(df_ready, core_factors)
    print(results.to_markdown(index=False))

    # 核心因子异质性研究
    top_factor = core_factors[0]

    print(f"\n【{top_factor}】在不同市场状态 (Market State) 下的表现:")
    market_stats = HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'market_state')
    print(market_stats.to_markdown())

    print(f"\n【{top_factor}】在不同行业板块 (Industry) 下的表现:")
    industry_stats = HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'industry')
    print(industry_stats.to_markdown())


if __name__ == '__main__':
    run_advanced_evaluation()