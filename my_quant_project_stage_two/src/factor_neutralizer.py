"""
Factor Neutralizer Module (因子标准化与中性化引擎)
包含截面 MAD 去极值、Z-score 标准化、以及 OLS 行业与市值中性化
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from typing import List

class FactorNeutralizer:
    """因子去极值、标准化与中性化引擎"""

    def __init__(self, mad_multiplier: float = 3.0):
        self.mad_multiplier = mad_multiplier

    def _mad_winsorize(self, s: pd.Series) -> pd.Series:
        """单列数据的 MAD 去极值"""
        median = s.median()
        mad = (s - median).abs().median()
        if mad == 0 or pd.isna(mad):
            return s
        upper = median + self.mad_multiplier * mad * 1.4826
        lower = median - self.mad_multiplier * mad * 1.4826
        return s.clip(lower=lower, upper=upper)

    @staticmethod
    def _zscore_standardize(s: pd.Series) -> pd.Series:
        """单列数据的 Z-score 标准化"""
        std = s.std()
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=s.index)
        return (s - s.mean()) / std

    def process_standardization(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        """
        在横截面 (每日) 上批量执行去极值与标准化
        """
        print(f"截面 MAD去极值({self.mad_multiplier}x) 与 Z-score标准化")
        df_out = df.copy()

        def process_cross_section(group):
            for col in factor_cols:
                if col in group.columns:
                    group[col] = self._zscore_standardize(self._mad_winsorize(group[col]))
            return group

        return df_out.groupby('date', group_keys=False).apply(process_cross_section)

    def neutralize_factors(self, df: pd.DataFrame, factor_cols: List[str], size_col: str = 'market_cap', industry_col: str = 'industry') -> pd.DataFrame:
        """
        OLS 行业与市值中性化 (Industry & Size Neutralization)
        Factor = beta_0 + beta_1 * Ln(Size) + beta_i * Industry_i + Residuals
        """
        print(f" OLS 行业与市值中性化回归提取纯净残差")
        df_out = df.copy()
        
        # 对市值取自然对数缓解偏态
        if size_col in df_out.columns:
            df_out['ln_size'] = np.log(df_out[size_col].replace(0, np.nan))
        else:
            raise ValueError(f"缺少市值列: {size_col}")

        def ols_neutralize(group):
            # 获取当前截面的有效数据
            valid_idx = group[factor_cols + ['ln_size', industry_col]].dropna().index
            if len(valid_idx) < 30: 
                return group
            
            sub_group = group.loc[valid_idx].copy()
            
            # 构建自变量 (X)：市值 + 行业哑变量 (Dummy Variables)
            X = sub_group[['ln_size']]
            industry_dummies = pd.get_dummies(sub_group[industry_col], drop_first=True, dtype=float)
            X = pd.concat([X, industry_dummies], axis=1)
            X = sm.add_constant(X)
            
            # 对每个因子执行截面回归提取残差
            for col in factor_cols:
                y = sub_group[col]
                try:
                    model = sm.OLS(y, X).fit()
                    # 用残差 (纯正Alpha) 替换原因子值
                    group.loc[valid_idx, col] = model.resid
                except Exception:
                    group.loc[valid_idx, col] = np.nan
            return group

        return df_out.groupby('date', group_keys=False).apply(ols_neutralize)