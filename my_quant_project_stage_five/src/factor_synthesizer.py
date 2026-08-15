"""
Multi-Factor Synthesizer Module (多因子动态加权合成引擎)
"""

from typing import List, Literal
import numpy as np
import pandas as pd
import scipy.stats as st


class FactorSynthesizer:
    """多因子合成与动态赋权计算器"""

    def __init__(self, min_periods: int = 6):
        self.min_periods = min_periods

    @staticmethod
    def _calc_monthly_ic_series(df: pd.DataFrame, factor_cols: List[str], target_col: str) -> pd.DataFrame:
        dates = sorted(df['date'].unique())
        ic_records = []

        for d in dates:
            sub_df = df[df['date'] == d].dropna(subset=factor_cols + [target_col])
            if len(sub_df) < 5:
                continue

            row_ic = {'date': d}
            y = sub_df[target_col]
            for col in factor_cols:
                x = sub_df[col]
                if x.nunique() > 1 and y.nunique() > 1:
                    ic, _ = st.spearmanr(x, y)
                    row_ic[col] = ic
                else:
                    row_ic[col] = np.nan
            ic_records.append(row_ic)

        return pd.DataFrame(ic_records).set_index('date').sort_index()

    def synthesize_equal_weight(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        df_out = df.copy()
        df_out['composite_score'] = df_out[factor_cols].mean(axis=1)
        return df_out

    def synthesize_ic_ir_weight(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        target_col: str = 'ret_next_month',
        rolling_window: int = 12,
        weight_metric: Literal['ic', 'ir'] = 'ir'
    ) -> pd.DataFrame:
        df_out = df.copy()
        ic_df = self._calc_monthly_ic_series(df_out, factor_cols, target_col)

        rolling_ic_mean = ic_df.rolling(window=rolling_window, min_periods=self.min_periods).mean().shift(1)
        rolling_ic_std = ic_df.rolling(window=rolling_window, min_periods=self.min_periods).std().shift(1)

        raw_weights = rolling_ic_mean / (rolling_ic_std + 1e-6) if weight_metric == 'ir' else rolling_ic_mean

        normalized_weights = raw_weights.apply(
            lambda row: row / row.abs().sum() if row.abs().sum() > 0 else pd.Series(1.0 / len(factor_cols), index=row.index),
            axis=1
        ).fillna(1.0 / len(factor_cols))

        scores = []
        for date, group in df_out.groupby('date', group_keys=False):
            w = normalized_weights.loc[date].values if date in normalized_weights.index else np.ones(len(factor_cols)) / len(factor_cols)
            F = group[factor_cols].values
            scores.extend(np.dot(F, w))

        df_out['composite_score'] = scores
        return df_out

    def synthesize_max_ir_weight(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        target_col: str = 'ret_next_month',
        rolling_window: int = 12,
        shrinkage_reg: float = 1e-3
    ) -> pd.DataFrame:
        df_out = df.copy()
        ic_df = self._calc_monthly_ic_series(df_out, factor_cols, target_col)
        dates = sorted(df_out['date'].unique())
        K = len(factor_cols)
        optimal_weights_dict = {}

        for d in dates:
            hist_ic = ic_df.loc[ic_df.index < d]
            if len(hist_ic) < self.min_periods:
                optimal_weights_dict[d] = np.ones(K) / K
                continue

            window_ic = hist_ic.tail(rolling_window)
            ic_mean = window_ic.mean().values
            cov_matrix = window_ic.cov().values

            if np.isnan(cov_matrix).any() or np.isnan(ic_mean).any():
                optimal_weights_dict[d] = np.ones(K) / K
                continue

            cov_reg = cov_matrix + shrinkage_reg * np.eye(K)
            try:
                inv_cov = np.linalg.pinv(cov_reg)
                w_opt = np.dot(inv_cov, ic_mean)
                sum_w = np.abs(w_opt).sum()
                w_opt = w_opt / sum_w if sum_w > 0 else np.ones(K) / K
            except Exception:
                w_opt = np.ones(K) / K

            optimal_weights_dict[d] = w_opt

        scores = []
        for date, group in df_out.groupby('date', group_keys=False):
            w = optimal_weights_dict.get(date, np.ones(K) / K)
            F = group[factor_cols].values
            scores.extend(np.dot(F, w))

        df_out['composite_score'] = scores
        return df_out

    def synthesize(
        self,
        df: pd.DataFrame,
        factor_cols: List[str],
        method: Literal['equal_weight', 'dynamic_ic', 'dynamic_ir', 'max_ir'] = 'equal_weight',
        target_col: str = 'ret_next_month',
        rolling_window: int = 12
    ) -> pd.DataFrame:
        if method == 'equal_weight':
            return self.synthesize_equal_weight(df, factor_cols)
        elif method == 'dynamic_ic':
            return self.synthesize_ic_ir_weight(df, factor_cols, target_col, rolling_window, weight_metric='ic')
        elif method == 'dynamic_ir':
            return self.synthesize_ic_ir_weight(df, factor_cols, target_col, rolling_window, weight_metric='ir')
        elif method == 'max_ir':
            return self.synthesize_max_ir_weight(df, factor_cols, target_col, rolling_window)
        else:
            raise ValueError(f"不支持的合成方法: {method}")