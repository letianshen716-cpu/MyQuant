"""
Factor Orthogonalizer Module (对称正交化去共线性引擎)
通过对称正交变换对齐因子信息，彻底剔除因子间多重共线性
"""

from typing import List
import numpy as np
import pandas as pd
from scipy.linalg import eigh


class FactorOrthogonalizer:
    """对称正交化计算器"""

    def __init__(self, min_stocks: int = 30):
        """
        :param min_stocks: 单一截面有效计算的最小样本股票数
        """
        self.min_stocks = min_stocks

    def process(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        """
        在每个截面上对输入的多维因子执行对称正交化 (Symmetric Orthogonalization)
        变化公式: S = U * Lambda^(-1/2) * U^T, F_orth = F * S
        """
        print(f"\n实施对称正交化处理，输入因子数: {len(factor_cols)}")
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

            # 计算重叠协方差矩阵 M = F^T * F / N
            M = np.dot(F.T, F) / N
            try:
                # 特征值分解
                eigenvalues, eigenvectors = eigh(M)
                # 设定极小下界，保证半正定与数值稳定
                eigenvalues = np.maximum(eigenvalues, 1e-8)
                inv_sqrt_eigenvalues = np.diag(1.0 / np.sqrt(eigenvalues))
                # 构造正交转换矩阵 S
                S = np.dot(eigenvectors, np.dot(inv_sqrt_eigenvalues, eigenvectors.T))
                # 正交化变换
                group[factor_cols] = np.dot(F, S)
            except Exception:
                pass

            return group

        return df_orth.groupby('date', group_keys=False).apply(symmetric_orth)