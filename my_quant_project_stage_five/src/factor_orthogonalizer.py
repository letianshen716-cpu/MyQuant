"""
Factor Orthogonalizer Module (对称正交化去共线性引擎)
"""

from typing import List
import numpy as np
import pandas as pd
from scipy.linalg import eigh


class FactorOrthogonalizer:
    """对称正交化计算器"""

    def __init__(self, min_stocks: int = 30):
        self.min_stocks = min_stocks

    def process(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        df_orth = df.copy()

        def symmetric_orth(group: pd.DataFrame) -> pd.DataFrame:
            if len(group) < self.min_stocks:
                for col in factor_cols:
                    group[col] = np.nan
                return group

            F = group[factor_cols].values
            F = np.nan_to_num(F)
            N = F.shape[0]
            if N == 0:
                return group

            M = np.dot(F.T, F) / N
            try:
                eigenvalues, eigenvectors = eigh(M)
                eigenvalues = np.maximum(eigenvalues, 1e-8)
                inv_sqrt_eigenvalues = np.diag(1.0 / np.sqrt(eigenvalues))
                S = np.dot(eigenvectors, np.dot(inv_sqrt_eigenvalues, eigenvectors.T))
                group[factor_cols] = np.dot(F, S)
            except Exception:
                pass

            return group

        return df_orth.groupby('date', group_keys=False).apply(symmetric_orth)