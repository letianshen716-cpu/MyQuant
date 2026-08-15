"""
MyQuant Core Algorithm & Processing Engine Package
封装底层数据处理、因子特征工程、统计筛选、策略回测及归因评估引擎
"""

from src.factor_evaluator import FactorEvaluator
from src.factor_orthogonalizer import FactorOrthogonalizer
from src.factor_synthesizer import FactorSynthesizer
from src.feature_builder import (
    build_fundamental_features,
    build_pit_wide_table,
    build_technical_features,
)
from src.heterogeneity_analyzer import HeterogeneityAnalyzer
from src.performance_attributor import PerformanceAttributor
from src.portfolio_backtester import PortfolioBacktester
from src.statistical_selector import StatisticalSelector

__all__ = [
    "FactorEvaluator",
    "FactorOrthogonalizer",
    "FactorSynthesizer",
    "HeterogeneityAnalyzer",
    "PerformanceAttributor",
    "PortfolioBacktester",
    "StatisticalSelector",
    "build_technical_features",
    "build_fundamental_features",
    "build_pit_wide_table",
]