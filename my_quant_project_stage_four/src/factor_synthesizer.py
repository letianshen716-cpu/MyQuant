"""
Multi-Factor Synthesizer Module (多因子动态加权合成引擎)
支持等权加权、滚动动态 IC/IC-IR 加权、最大化复合 IR 优化加权
"""

from typing import List, Literal
import numpy as np
import pandas as pd
import scipy.stats as st


class FactorSynthesizer:
    """多因子合成与动态赋权计算器"""

    def __init__(self, min_periods: int = 6):
        """
        :param min_periods: 滚动计算历史指标所需的最小有效月数
        """
        self.min_periods = min_periods

    @staticmethod
    def _calc_monthly_ic_series(df: pd.DataFrame, factor_cols: List[str], target_col: str) -> pd.DataFrame:
        """
        按月度截面计算各因子的 Spearman Rank IC 时间序列
        """
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

        ic_df = pd.DataFrame(ic_records).set_index('date').sort_index()
        return ic_df

    def synthesize_equal_weight(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        """
        等权加权合成
        Score_i = 1/K * \sum f_{i,k}
        """
        print(f"正在执行等权合成，因子数: {len(factor_cols)}")
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
        """
        滚动动态 IC / IC-IR 动态加权
        严格采用历史 t-1 期以前的数据计算当期权重，防范前瞻偏差

        :param df: 输入因子宽表
        :param factor_cols: 参与合成的因子列
        :param target_col: 目标未来收益率列
        :param rolling_window: 滚动窗口大小 (月)
        :param weight_metric: 'ic' (基于平均IC加权) 或 'ir' (基于IC/Std加权)
        """
        print(f"滚动 {rolling_window} 个月的动态 {weight_metric.upper()} 权重")
        df_out = df.copy()

        # 1. 计算历史 IC 时序
        ic_df = self._calc_monthly_ic_series(df_out, factor_cols, target_col)

        # 2. 计算滚动均值与标准差 (shift 1 个月避免引入当月未来信息)
        rolling_ic_mean = ic_df.rolling(window=rolling_window, min_periods=self.min_periods).mean().shift(1)
        rolling_ic_std = ic_df.rolling(window=rolling_window, min_periods=self.min_periods).std().shift(1)

        if weight_metric == 'ir':
            raw_weights = rolling_ic_mean / (rolling_ic_std + 1e-6)
        else:
            raw_weights = rolling_ic_mean

        # 3. 权重归一化 (若无足够历史数据，默认回退至等权 1/K)
        normalized_weights = raw_weights.apply(
            lambda row: row / row.abs().sum() if row.abs().sum() > 0 else pd.Series(1.0 / len(factor_cols), index=row.index),
            axis=1
        ).fillna(1.0 / len(factor_cols))

        # 4. 逐截面向量化矩阵乘法计算复合得分
        scores = []
        for date, group in df_out.groupby('date', group_keys=False):
            w = normalized_weights.loc[date].values if date in normalized_weights.index else np.ones(len(factor_cols)) / len(factor_cols)
            F = group[factor_cols].values
            composite = np.dot(F, w)
            scores.extend(composite)

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
        """
        最大化复合 IR 优化加权
        目标权重 w^* ∝ (\Sigma + \lambda I)^{-1} * IC
        结合压缩协方差估计 (Shrinkage Regularization)，抑制病态逆矩阵的扰动

        :param df: 输入因子宽表
        :param factor_cols: 参与合成的因子列
        :param target_col: 目标未来收益率列
        :param rolling_window: 历史滚动窗口 (月)
        :param shrinkage_reg: 协方差对角岭正则化系数
        """
        print(f"正在求解最大化复合 IR 一阶最优权重，窗口: {rolling_window}M, 正则: {shrinkage_reg}")
        df_out = df.copy()

        # 1. 计算历史 IC 时序
        ic_df = self._calc_monthly_ic_series(df_out, factor_cols, target_col)
        dates = sorted(df_out['date'].unique())
        K = len(factor_cols)
        optimal_weights_dict = {}

        # 2. 滚动求解逆矩阵权重 (严格使用 t-1 以前的历史窗口)
        for i, d in enumerate(dates):
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

            # 加入对角岭正则化项
            cov_reg = cov_matrix + shrinkage_reg * np.eye(K)

            try:
                # 求解 w^* = Cov^{-1} * IC
                inv_cov = np.linalg.pinv(cov_reg)
                w_opt = np.dot(inv_cov, ic_mean)
                sum_w = np.abs(w_opt).sum()
                w_opt = w_opt / sum_w if sum_w > 0 else np.ones(K) / K
            except Exception:
                w_opt = np.ones(K) / K

            optimal_weights_dict[d] = w_opt

        # 3. 映射至截面数据
        scores = []
        for date, group in df_out.groupby('date', group_keys=False):
            w = optimal_weights_dict.get(date, np.ones(K) / K)
            F = group[factor_cols].values
            composite = np.dot(F, w)
            scores.extend(composite)

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
        """
        统一多因子合成调度入口
        """
        if method == 'equal_weight':
            return self.synthesize_equal_weight(df, factor_cols)
        elif method == 'dynamic_ic':
            return self.synthesize_ic_ir_weight(df, factor_cols, target_col, rolling_window, weight_metric='ic')
        elif method == 'dynamic_ir':
            return self.synthesize_ic_ir_weight(df, factor_cols, target_col, rolling_window, weight_metric='ir')
        elif method == 'max_ir':
            return self.synthesize_max_ir_weight(df, factor_cols, target_col, rolling_window)
        else:
            raise ValueError(f"不支持的合成方法: {method}。可选范围: ['equal_weight', 'dynamic_ic', 'dynamic_ir', 'max_ir']")