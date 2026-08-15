"""
Script 04: 多因子选股策略全样本回测
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config.settings import BACKTEST_CONFIG, PROCESSED_DATA_DIR, WIDE_TABLE_PATH
from src.factor_evaluator import FactorEvaluator
from src.factor_orthogonalizer import FactorOrthogonalizer
from src.factor_synthesizer import FactorSynthesizer
from src.portfolio_backtester import PortfolioBacktester
from src.statistical_selector import StatisticalSelector

def run_strategy_pipeline():

    df = pd.read_parquet(WIDE_TABLE_PATH)
    factor_cols = [col for col in ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe'] if col in df.columns]

    for col in ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d']:
        if col in factor_cols:
            df[col] = df[col] * -1.0

    min_stocks = BACKTEST_CONFIG.get('min_stocks_per_cross', 30)
    friction = BACKTEST_CONFIG.get('friction_cost', 0.003)

    evaluator = FactorEvaluator(friction_cost=friction, min_stocks=min_stocks)
    orthogonalizer = FactorOrthogonalizer(min_stocks=min_stocks)

    df_ready = evaluator.preprocess_cross_section(
        orthogonalizer.process(evaluator.preprocess_cross_section(df, factor_cols), factor_cols), factor_cols
    )

    core_factors = StatisticalSelector.select_factors(df_ready, factor_cols)
    synthesizer = FactorSynthesizer()
    backtester = PortfolioBacktester(top_n=BACKTEST_CONFIG.get('hold_top_n', 50), friction_cost=friction)

    synthesis_methods = [
        ('Equal Weight (等权基准)', 'equal_weight'),
        ('Dynamic IC-IR (动态IC-IR加权)', 'dynamic_ir'),
        ('Max Composite IR (最大化复合IR优化)', 'max_ir')
    ]

    summary_metrics = []
    best_nav_df = None
    best_holdings_df = None
    highest_sharpe = -999.0

    for display_name, method in synthesis_methods:
        df_scored = synthesizer.synthesize(df=df_ready, factor_cols=core_factors, method=method)
        nav_df, holdings_df, metrics = backtester.run_backtest(df_scored)
        
        metrics_record = {'Synthesis Method': display_name}
        metrics_record.update(metrics)
        summary_metrics.append(metrics_record)

        if metrics.get('Sharpe Ratio', 0.0) > highest_sharpe:
            highest_sharpe = metrics.get('Sharpe Ratio', 0.0)
            best_nav_df = nav_df
            best_holdings_df = holdings_df

    print("\n多因子加权方案回测绩效对比总表")
    print(pd.DataFrame(summary_metrics).to_markdown(index=False))

    if best_nav_df is not None:
        best_nav_df.to_csv(PROCESSED_DATA_DIR / "backtest_monthly_nav.csv", encoding='utf-8-sig')
        best_holdings_df.to_csv(PROCESSED_DATA_DIR / "backtest_holdings_records.csv", index=False, encoding='utf-8-sig')
        pd.DataFrame(summary_metrics).to_csv(PROCESSED_DATA_DIR / "backtest_performance_metrics.csv", index=False)

if __name__ == '__main__':
    run_strategy_pipeline()