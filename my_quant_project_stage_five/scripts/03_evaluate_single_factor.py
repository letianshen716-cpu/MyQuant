"""
Script 03: 单因子批量检验、正交化与异质性分析
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
        print("未找到大宽表文件")
        return

    df = pd.read_parquet(WIDE_TABLE_PATH)
    target_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe']
    factor_cols = [col for col in target_factors if col in df.columns and not df[col].isna().all()]

    reversal_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d']
    for col in reversal_factors:
        if col in factor_cols:
            df[col] = df[col] * -1.0

    min_stocks = BACKTEST_CONFIG.get('min_stocks_per_cross', 30)
    evaluator = FactorEvaluator(friction_cost=BACKTEST_CONFIG.get('friction_cost', 0.003), min_stocks=min_stocks)
    orthogonalizer = FactorOrthogonalizer(min_stocks=min_stocks)

    print("\n执行预处理与正交化")
    df_std = evaluator.preprocess_cross_section(df, factor_cols)
    df_orth = orthogonalizer.process(df_std, factor_cols)
    df_ready = evaluator.preprocess_cross_section(df_orth, factor_cols)

    core_factors = StatisticalSelector.select_factors(df_ready, factor_cols)
    if not core_factors:
        return

    print("\n批量检验核心因子")
    results = evaluator.run_batch_evaluation(df_ready, core_factors)
    print(results.to_markdown(index=False))

    top_factor = core_factors[0]
    print(f"\n异质性分析: 【{top_factor}】")
    print(HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'market_state').to_markdown())
    print("\n")
    print(HeterogeneityAnalyzer.analyze(df_ready, top_factor, 'industry').to_markdown())

if __name__ == '__main__':
    run_advanced_evaluation()