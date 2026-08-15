"""
Factor Evaluator Module (单因子有效性实证检验引擎)
包含横截面 MAD 去极值、Z-score 标准化、Rank IC/IR 计算与分层回测
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import scipy.stats as st


class FactorEvaluator:
    """多因子批量截面清洗与统计显著性评估引擎"""

    def __init__(
        self,
        friction_cost: float = 0.003,
        min_stocks: int = 30,
        mad_multiplier: float = 3.0,
        quantiles: int = 5
    ):
        self.friction_cost = friction_cost
        self.min_stocks = min_stocks
        self.mad_multiplier = mad_multiplier
        self.quantiles = quantiles

    def _mad_winsorize(self, s: pd.Series) -> pd.Series:
        median = s.median()
        mad = (s - median).abs().median()
        if mad == 0 or pd.isna(mad):
            return s
        upper = median + self.mad_multiplier * mad * 1.4826
        lower = median - self.mad_multiplier * mad * 1.4826
        return s.clip(lower=lower, upper=upper)

    @staticmethod
    def _zscore_standardize(s: pd.Series) -> pd.Series:
        std = s.std()
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std

    def preprocess_cross_section(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
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
        df_valid = df.dropna(subset=[factor_name, target_col]).copy()
        df_valid = df_valid[(df_valid[target_col] >= -0.5) & (df_valid[target_col] <= 2.0)]

        if df_valid.empty:
            return {
                'Factor': factor_name, 'IC Mean': np.nan, 'IR': np.nan,
                'IC Win Rate': "0.00%", 'G1 Return (x)': np.nan, 'G5 Return (x)': np.nan, 'Long-Short Spread': np.nan
            }

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

        labels = [f'G{i+1}' for i in range(self.quantiles)]

        def assign_quantiles(x: pd.Series) -> pd.Series:
            if x.count() < self.min_stocks:
                return pd.Series(np.nan, index=x.index)
            return pd.qcut(x.rank(method='first'), q=self.quantiles, labels=labels)

        df_valid['group'] = df_valid.groupby('date')[factor_name].transform(assign_quantiles)
        monthly_returns = df_valid.groupby(['date', 'group'], observed=True)[target_col].mean().unstack()
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
        results = []
        for factor in factor_cols:
            res = self.evaluate_single_factor(df, factor, target_col)
            results.append(res)
        return pd.DataFrame(results)