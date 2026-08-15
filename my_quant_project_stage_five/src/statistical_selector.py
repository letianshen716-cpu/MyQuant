"""
Statistical Selector Module (统计学习特征筛选引擎)
具备小样本正交因子智能保护机制与高维 LassoCV 正则化筛选
"""

from typing import List
import numpy as np
import pandas as pd
from sklearn.linear_model import LassoCV


class StatisticalSelector:
    """特征有效性评估与筛选器"""

    @staticmethod
    def select_factors(
        df: pd.DataFrame,
        factor_cols: List[str],
        target_col: str = 'ret_next_month',
        min_coef: float = 1e-6
    ) -> List[str]:
        if len(factor_cols) <= 10:
            return factor_cols

        df_valid = df.dropna(subset=factor_cols + [target_col]).copy()
        df_valid = df_valid[(df_valid[target_col] >= -0.5) & (df_valid[target_col] <= 2.0)]

        if df_valid.empty:
            return factor_cols

        X, y = df_valid[factor_cols], df_valid[target_col]
        cv_folds = min(5, len(df_valid) // 2)

        if cv_folds < 2:
            return factor_cols

        try:
            alphas_grid = [1e-6, 5e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2]
            lasso = LassoCV(alphas=alphas_grid, cv=cv_folds, random_state=42, n_jobs=-1, max_iter=10000)
            lasso.fit(X, y)
            
            importance = pd.Series(np.abs(lasso.coef_), index=factor_cols)
            selected = importance[importance > min_coef].sort_values(ascending=False).index.tolist()
            return selected if selected else factor_cols

        except Exception:
            return factor_cols