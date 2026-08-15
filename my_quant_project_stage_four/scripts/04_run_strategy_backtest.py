"""
Script 04: 多因子选股策略全样本回测与稳健性检验
对比不同因子加权合成方案，执行全样本区间回测并输出全维度绩效指标与持仓流水
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

    if not WIDE_TABLE_PATH.exists():
        return
    df = pd.read_parquet(WIDE_TABLE_PATH)

    target_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'roe']
    factor_cols = [col for col in target_factors if col in df.columns and not df[col].isna().all()]

    # 因子方向反转校正
    reversal_factors = ['momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d']
    for col in reversal_factors:
        if col in factor_cols:
            df[col] = df[col] * -1.0

    min_stocks = BACKTEST_CONFIG.get('min_stocks_per_cross', 30)
    friction = BACKTEST_CONFIG.get('friction_cost', 0.003)

    # 截面预处理与对称正交化
    evaluator = FactorEvaluator(friction_cost=friction, min_stocks=min_stocks)
    orthogonalizer = FactorOrthogonalizer(min_stocks=min_stocks)

    df_std = evaluator.preprocess_cross_section(df, factor_cols)
    df_orth = orthogonalizer.process(df_std, factor_cols)
    df_ready = evaluator.preprocess_cross_section(df_orth, factor_cols)

    # 特征筛选
    core_factors = StatisticalSelector.select_factors(df_ready, factor_cols)
    print(f"\n参与组合合成的核心因子集合: {core_factors}")

    synthesizer = FactorSynthesizer(min_periods=6)
    backtester = PortfolioBacktester(
        top_n=BACKTEST_CONFIG.get('hold_top_n', 50),
        friction_cost=friction,
        weighting_method='equal',
        annual_periods=12,
        risk_free_rate=0.02
    )

    synthesis_methods = [
        ('Equal Weight (等权基准)', 'equal_weight'),
        ('Dynamic IC-IR (动态IC-IR加权)', 'dynamic_ir'),
        ('Max Composite IR (最大化复合IR优化)', 'max_ir')
    ]

    summary_metrics = []
    best_nav_df = None
    best_holdings_df = None
    best_method_name = ""
    highest_sharpe = -999.0


    for display_name, method in synthesis_methods:
        print(f"\n方案: 【{display_name}】")
        df_scored = synthesizer.synthesize(
            df=df_ready,
            factor_cols=core_factors,
            method=method,
            rolling_window=12
        )

        nav_df, holdings_df, metrics = backtester.run_backtest(
            df=df_scored,
            score_col='composite_score',
            ret_col='ret_next_month'
        )

        metrics_record = {'Synthesis Method': display_name}
        metrics_record.update(metrics)
        summary_metrics.append(metrics_record)

        # 记录表现最佳的模型用于落盘
        if metrics.get('Sharpe Ratio', 0.0) > highest_sharpe:
            highest_sharpe = metrics.get('Sharpe Ratio', 0.0)
            best_nav_df = nav_df
            best_holdings_df = holdings_df
            best_method_name = display_name

    # 输出多方案对比总表
    df_summary = pd.DataFrame(summary_metrics)
    print(df_summary.to_markdown(index=False))

    if best_nav_df is not None and best_holdings_df is not None:
        nav_file = PROCESSED_DATA_DIR / "backtest_monthly_nav.csv"
        holdings_file = PROCESSED_DATA_DIR / "backtest_holdings_records.csv"
        metrics_file = PROCESSED_DATA_DIR / "backtest_performance_metrics.csv"

        best_nav_df.to_csv(nav_file, encoding='utf-8-sig')
        best_holdings_df.to_csv(holdings_file, index=False, encoding='utf-8-sig')
        df_summary.to_csv(metrics_file, index=False, encoding='utf-8-sig')

        print(f"\n最优模型【{best_method_name}】的净值与持仓明细已成功落盘：")
        print(f"逐月净值时序: {nav_file}")
        print(f"持仓变动流水: {holdings_file}")
        print(f"绩效指标汇总: {metrics_file}")
    
    if best_nav_df is not None:
        nav_series = best_nav_df.copy()
        nav_series.index = pd.to_datetime(nav_series.index)
        
        # 划分牛熊子区间
        sub_periods = {
            "2020-2022 (震荡分化期)": nav_series.loc[nav_series.index < '2023-01-01'],
            "2023-2026 (轮动修复期)": nav_series.loc[nav_series.index >= '2023-01-01']
        }
        
        sub_results = []
        for period_name, sub_df in sub_periods.items():
            if len(sub_df) > 3:
                sub_metrics = backtester.calculate_performance_metrics(sub_df.copy())
                rec = {'Sub Period': period_name}
                rec.update(sub_metrics)
                sub_results.append(rec)
                
        if sub_results:
            df_sub_summary = pd.DataFrame(sub_results)
            print(df_sub_summary.to_markdown(index=False))


if __name__ == '__main__':
    run_strategy_pipeline()