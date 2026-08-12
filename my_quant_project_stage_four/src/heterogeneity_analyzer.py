"""
Heterogeneity Analyzer Module (因子异质性分析引擎)
检验核心因子在不同市场状态 (Bull/Bear) 与行业板块下的表现差异
"""

import numpy as np
import pandas as pd
import scipy.stats as st


class HeterogeneityAnalyzer:
    """因子异质性分析器"""

    @staticmethod
    def analyze(
        df: pd.DataFrame,
        factor: str,
        group_col: str,
        target_col: str = 'ret_next_month',
        min_stocks: int = 5
    ) -> pd.DataFrame:
        """
        在给定的分类维度 (group_col) 下分组计算 Rank IC、IR 及胜率
        """
        df_valid = df.dropna(subset=[factor, target_col, group_col]).copy()
        df_valid = df_valid[(df_valid[target_col] >= -0.5) & (df_valid[target_col] <= 2.0)]

        if df_valid.empty:
            return pd.DataFrame()

        def calc_ic(group: pd.DataFrame) -> float:
            if len(group) >= min_stocks and group[factor].nunique() > 1 and group[target_col].nunique() > 1:
                ic, _ = st.spearmanr(group[factor], group[target_col])
                return ic
            return np.nan

        # 双重聚合：[日期, 分组类别]
        ic_panel = df_valid.groupby(['date', group_col]).apply(calc_ic).reset_index(name='IC')
        ic_panel = ic_panel.dropna(subset=['IC'])

        if ic_panel.empty:
            return pd.DataFrame()

        stats = ic_panel.groupby(group_col)['IC'].agg(
            IC_Mean='mean',
            IC_Std='std'
        )
        stats['IR'] = stats['IC_Mean'] / (stats['IC_Std'] + 1e-6)
        stats['Win_Rate'] = ic_panel.groupby(group_col).apply(lambda x: (x['IC'] > 0).mean())

        return stats.fillna(0.0).round(4)