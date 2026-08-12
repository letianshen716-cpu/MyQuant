"""
Statistical Selector Module (统计学习特征筛选引擎)
包含小样本正交保护机制与高维 LassoCV L1 正则化惩罚回归
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
        """
        根据输入维度智能选择筛选策略
        """
        print(f"\n>>> [特征选择] 执行特征有效性评估 (候选因子: {len(factor_cols)})")
        
       
        if len(factor_cols) <= 10:
            print(f"   -> 侦测到候选因子数较少 (仅 {len(factor_cols)} 个)，且已在前置步骤完成正交化。")
            print("   -> 极低信噪比环境下，对少量独立核心信号执行 Lasso 易导致信号被过度惩罚。")
            print("   -> 触发智能保护机制：跳过 Lasso 稀疏化，全量保留进入多因子组合回测！")
            return factor_cols


        df_valid = df.dropna(subset=factor_cols + [target_col]).copy()
        df_valid = df_valid[(df_valid[target_col] >= -0.5) & (df_valid[target_col] <= 2.0)]

        if df_valid.empty:
            print("有效样本量不足，保留全部原始因子。")
            return factor_cols

        X, y = df_valid[factor_cols], df_valid[target_col]
        cv_folds = min(5, len(df_valid) // 2)

        if cv_folds < 2:
            return factor_cols

        try:
            alphas_grid = [1e-6, 5e-6, 1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3, 1e-2]
            lasso = LassoCV(alphas=alphas_grid, cv=cv_folds, random_state=42, n_jobs=-1, max_iter=10000)
            lasso.fit(X, y)
            
            print(f"   -> 最佳 L1 惩罚系数 (Alpha): {lasso.alpha_:.6f}")
            
            importance = pd.Series(np.abs(lasso.coef_), index=factor_cols)
            selected = importance[importance > min_coef].sort_values(ascending=False).index.tolist()
            
            if selected:
                print(f"   -> LassoCV 筛选完毕。保留核心因子数: {len(selected)}")
                return selected
            else:
                print("   -> 降级处理：筛选后无有效因子，强制回退并保留全部原始因子。")
                return factor_cols

        except Exception as e:
            print(f" LassoCV 执行异常: {e}")
            return factor_cols