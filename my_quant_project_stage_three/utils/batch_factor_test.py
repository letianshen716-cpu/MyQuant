import pandas as pd
import numpy as np
import scipy.stats as st

class BatchFactorEvaluator:
    """
    多因子批量检验引擎
    支持横截面去极值、标准化，批量输出 IC/IR 与分层回测结果
    """
    def __init__(self, friction_cost=0.003, min_stocks=30):
        self.friction_cost = friction_cost # 单边调仓摩擦成本
        self.min_stocks = min_stocks       # 截面最小股票数要求

    def _mad_winsorize(self, s: pd.Series, n=3) -> pd.Series:
        """绝对中位差 (MAD) 去极值法"""
        median = s.median()
        mad = (s - median).abs().median()
        upper = median + n * mad * 1.4826
        lower = median - n * mad * 1.4826
        return s.clip(lower=lower, upper=upper)

    def _zscore_standardize(self, s: pd.Series) -> pd.Series:
        """Z-score 标准化"""
        return (s - s.mean()) / s.std()

    def preprocess_cross_section(self, df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
        """对所有因子按日期进行横截面去极值与标准化"""
        print("横截面数据预处理 (MAD去极值 + Z-score标准化)")
        df_processed = df.copy()
        
        def process_daily(group):
            for col in factor_cols:
                if group[col].count() > self.min_stocks:
                    group[col] = self._zscore_standardize(self._mad_winsorize(group[col]))
                else:
                    group[col] = np.nan
            return group
            
        return df_processed.groupby('date', group_keys=False).apply(process_daily)

    def evaluate_single_factor(self, df: pd.DataFrame, factor_name: str) -> dict:
        """对单个因子进行统计显著性与分组收益检验"""
        df_valid = df.dropna(subset=[factor_name, 'ret_next_month']).copy()
        
        # 计算 Rank IC
        def calc_ic(group):
            if len(group) > self.min_stocks:
                ic, _ = st.spearmanr(group[factor_name], group['ret_next_month'])
                return ic
            return np.nan

        ic_series = df_valid.groupby('date').apply(calc_ic).dropna()
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        ir = ic_mean / ic_std if ic_std != 0 else 0
        win_rate = (ic_series > 0).mean()

        # 分层回测 (5组)
        def get_quantiles(group):
            if len(group) < self.min_stocks:
                return pd.Series(float('nan'), index=group.index)
            labels = ['G1', 'G2', 'G3', 'G4', 'G5']
            return pd.qcut(group[factor_name].rank(method='first'), q=5, labels=labels)

        df_valid['group'] = df_valid.groupby('date', group_keys=False).apply(get_quantiles)
        monthly_returns = df_valid.groupby(['date', 'group'])['ret_next_month'].mean().unstack()
        
        # 扣除摩擦成本计算累积复利
        monthly_returns_net = monthly_returns - self.friction_cost
        cum_returns = (1 + monthly_returns_net).cumprod().iloc[-1]

        return {
            'Factor': factor_name,
            'IC Mean': round(ic_mean, 4),
            'IR': round(ir, 4),
            'IC Win Rate': f"{win_rate:.2%}",
            'G1 Return (x)': round(cum_returns.get('G1', 0), 2),
            'G5 Return (x)': round(cum_returns.get('G5', 0), 2),
            'Long-Short Spread': round(cum_returns.get('G5', 0) - cum_returns.get('G1', 0), 2)
        }

    def run_batch_evaluation(self, df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
        """运行所有因子的批量检验并输出汇总表"""
        print(f"开始批量检验 {len(factor_cols)} 个因子")
        df_clean = self.preprocess_cross_section(df, factor_cols)
        
        results = []
        for i, factor in enumerate(factor_cols, 1):
            print(f"   [{i}/{len(factor_cols)}] 正在验证: {factor}")
            res = self.evaluate_single_factor(df_clean, factor)
            results.append(res)
            
        df_results = pd.DataFrame(results)
        print("\n全局 Alpha 能力汇总如下：")
        return df_results