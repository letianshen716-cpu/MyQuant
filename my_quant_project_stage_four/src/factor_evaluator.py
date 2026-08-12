"""
Factor Evaluator Module (单因子有效性实证检验引擎)
包含横截面 MAD 去极值、Z-score 标准化、Rank IC/IR 计算与分层回测
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import scipy.stats as st


class FactorEvaluator:
    """
    多因子批量截面清洗与统计显著性评估引擎
    """

    def __init__(
        self,
        friction_cost: float = 0.003,
        min_stocks: int = 30,
        mad_multiplier: float = 3.0,
        quantiles: int = 5
    ):
        """
        :param friction_cost: 单边调仓交易摩擦成本 (默认 0.3%)
        :param min_stocks: 单一截面有效计算的最小样本股票数
        :param mad_multiplier: MAD 去极值倍数 (默认 3.0 倍)
        :param quantiles: 分层回测分组数量 (默认 5 分组)
        """
        self.friction_cost = friction_cost
        self.min_stocks = min_stocks
        self.mad_multiplier = mad_multiplier
        self.quantiles = quantiles

    def _mad_winsorize(self, s: pd.Series) -> pd.Series:
        """三倍中位绝对离差法 (MAD) 去极值"""
        median = s.median()
        mad = (s - median).abs().median()

        # 样本过小或全同分布时防崩溃
        if mad == 0 or pd.isna(mad):
            return s

        upper = median + self.mad_multiplier * mad * 1.4826
        lower = median - self.mad_multiplier * mad * 1.4826
        return s.clip(lower=lower, upper=upper)

    @staticmethod
    def _zscore_standardize(s: pd.Series) -> pd.Series:
        """Z-score 标准化"""
        std = s.std()
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std

    def preprocess_cross_section(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        """
        对指定因子在每个交易日截面上独立执行 MAD 去极值与 Z-score 标准化
        """
        print(f">>> [预处理] 正在执行横截面 MAD 去极值 (倍数: {self.mad_multiplier}) 与 Z-score 标准化...")
        df_processed = df.copy()

        def process_daily(group: pd.DataFrame) -> pd.DataFrame:
            for col in factor_cols:
                if col in group.columns and group[col].count() >= self.min_stocks:
                    group[col] = self._zscore_standardize(self._mad_winsorize(group[col]))
                else:
                    group[col] = np.nan
            return group

        return df_processed.groupby('date', group_keys=False).apply(process_daily)

    def evaluate_single_factor(
        self,
        df: pd.DataFrame,
        factor_name: str,
        target_col: str = 'ret_next_month'
    ) -> Dict[str, Optional[float]]:
        """
        评估单个因子的 Rank IC、IR、IC 胜率与分层累计净值
        """
        df_valid = df.dropna(subset=[factor_name, target_col]).copy()
        # 剔除脏数据与极端涨跌幅
        df_valid = df_valid[(df_valid[target_col] >= -0.5) & (df_valid[target_col] <= 2.0)]

        if df_valid.empty:
            return {
                'Factor': factor_name, 'IC Mean': np.nan, 'IR': np.nan,
                'IC Win Rate': "0.00%", 'G1 Return (x)': np.nan, 'G5 Return (x)': np.nan, 'Long-Short Spread': np.nan
            }

        # 1. 计算月度 Rank IC 时序
        def calc_ic(group: pd.DataFrame) -> float:
            if len(group) >= self.min_stocks and group[factor_name].nunique() > 1 and group[target_col].nunique() > 1:
                ic, _ = st.spearmanr(group[factor_name], group[target_col])
                return ic
            return np.nan

        ic_series = df_valid.groupby('date').apply(calc_ic).dropna()
        ic_mean = ic_series.mean() if not ic_series.empty else 0.0
        ic_std = ic_series.std() if not ic_series.empty else 0.0
        ir = ic_mean / ic_std if ic_std != 0 else 0.0
        win_rate = (ic_series > 0).mean() if not ic_series.empty else 0.0

        # 2. 分层收益回测 (Q1 ~ Q5)
        labels = [f'G{i+1}' for i in range(self.quantiles)]

        def assign_quantiles(x: pd.Series) -> pd.Series:
            if x.count() < self.min_stocks:
                return pd.Series(np.nan, index=x.index)
            return pd.qcut(x.rank(method='first'), q=self.quantiles, labels=labels)

        df_valid['group'] = df_valid.groupby('date')[factor_name].transform(assign_quantiles)
        monthly_returns = df_valid.groupby(['date', 'group'], observed=True)[target_col].mean().unstack()
        # 扣除换仓摩擦成本
        monthly_returns_net = monthly_returns - self.friction_cost

        if monthly_returns_net.empty:
            cum_returns = pd.Series({'G1': 1.0, labels[-1]: 1.0})
        else:
            cum_returns = (1.0 + monthly_returns_net.fillna(0.0)).cumprod().iloc[-1]

        g1_ret = cum_returns.get('G1', 1.0)
        g_top_ret = cum_returns.get(labels[-1], 1.0)

        return {
            'Factor': factor_name,
            'IC Mean': round(float(ic_mean), 4),
            'IR': round(float(ir), 4),
            'IC Win Rate': f"{win_rate:.2%}",
            'G1 Return (x)': round(float(g1_ret), 2),
            f'{labels[-1]} Return (x)': round(float(g_top_ret), 2),
            'Long-Short Spread': round(float(g_top_ret - g1_ret), 2)
        }

    def run_batch_evaluation(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        target_col: str = 'ret_next_month'
    ) -> pd.DataFrame:
        """批量运行全量单因子实证检验"""
        print(f"\n>>> [批量检验] 开始检验 {len(factor_cols)} 个目标因子...")
        results = []
        for i, factor in enumerate(factor_cols, 1):
            print(f"   [{i}/{len(factor_cols)}] 正在验证: {factor}")
            res = self.evaluate_single_factor(df, factor, target_col)
            results.append(res)

        return pd.DataFrame(results)