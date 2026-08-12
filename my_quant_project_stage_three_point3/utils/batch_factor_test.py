import pandas as pd
import numpy as np
import scipy.stats as st
from scipy.linalg import eigh
from sklearn.linear_model import LassoCV
import warnings

# 忽略所有底层数学警告，保持控制台整洁
warnings.filterwarnings('ignore')

class BatchFactorEvaluator:
    """
    多因子批量检验引擎
    支持横截面去极值、标准化，批量输出 IC/IR 与分层回测结果
    """
    def __init__(self, friction_cost=0.003, min_stocks=3):
        self.friction_cost = friction_cost
        self.min_stocks = min_stocks

    def _mad_winsorize(self, s: pd.Series, n=3) -> pd.Series:
        """绝对中位差 (MAD) 去极值法"""
        median = s.median()
        mad = (s - median).abs().median()
        
        # 【核心修复1】：如果 MAD 为 0（小样本极易发生），直接返回原值，防止把所有数据抹平
        if mad == 0 or pd.isna(mad):
            return s
            
        upper = median + n * mad * 1.4826
        lower = median - n * mad * 1.4826
        return s.clip(lower=lower, upper=upper)

    def _zscore_standardize(self, s: pd.Series) -> pd.Series:
        """Z-score 标准化"""
        std = s.std()
        
        # 【核心修复2】：如果标准差为 0，防止触发除以 0 导致全列变成 NaN
        if pd.isna(std) or std == 0:
            return pd.Series(0.0, index=s.index)
            
        return (s - s.mean()) / std

    def preprocess_cross_section(self, df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
        """对所有因子按日期进行横截面去极值与标准化"""
        print("横截面数据预处理 (MAD去极值 + Z-score标准化)")
        df_processed = df.copy()
        
        def process_daily(group):
            for col in factor_cols:
                # 【核心修复3】：放宽存活条件，改成 >= 防止被卡死
                if group[col].count() >= self.min_stocks:
                    group[col] = self._zscore_standardize(self._mad_winsorize(group[col]))
                else:
                    group[col] = np.nan
            return group
            
        return df_processed.groupby('date', group_keys=False).apply(process_daily)

    def evaluate_single_factor(self, df: pd.DataFrame, factor_name: str) -> dict:
        """对单个因子进行统计显著性与分组收益检验"""
        df_valid = df.dropna(subset=[factor_name, 'ret_next_month']).copy()
        
        # 剔除极端收益率脏数据
        df_valid = df_valid[(df_valid['ret_next_month'] >= -0.5) & (df_valid['ret_next_month'] <= 2.0)]
        
        if df_valid.empty:
            return {
                'Factor': factor_name, 'IC Mean': np.nan, 'IR': np.nan,
                'IC Win Rate': "0.00%", 'G1 Return (x)': np.nan, 'G5 Return (x)': np.nan, 'Long-Short Spread': np.nan
            }

        def calc_ic(group):
            if len(group) >= self.min_stocks and group[factor_name].nunique() > 1 and group['ret_next_month'].nunique() > 1:
                ic, _ = st.spearmanr(group[factor_name], group['ret_next_month'])
                return ic
            return np.nan

        ic_series = df_valid.groupby('date').apply(calc_ic).dropna()
        ic_mean = ic_series.mean() if not ic_series.empty else 0
        ic_std = ic_series.std() if not ic_series.empty else 0
        ir = ic_mean / ic_std if ic_std != 0 else 0
        win_rate = (ic_series > 0).mean() if not ic_series.empty else 0

        def assign_quantiles(x):
            if x.count() < self.min_stocks:
                return pd.Series(np.nan, index=x.index)
            labels = ['G1', 'G2', 'G3', 'G4', 'G5']
            return pd.qcut(x.rank(method='first'), q=5, labels=labels)

        df_valid['group'] = df_valid.groupby('date')[factor_name].transform(assign_quantiles)
        monthly_returns = df_valid.groupby(['date', 'group'], observed=True)['ret_next_month'].mean().unstack()
        monthly_returns_net = monthly_returns - self.friction_cost
        
        if monthly_returns_net.empty:
            cum_returns = pd.Series({'G1': 1.0, 'G5': 1.0})
        else:
            cum_returns = (1 + monthly_returns_net.fillna(0)).cumprod().iloc[-1]

        return {
            'Factor': factor_name,
            'IC Mean': round(ic_mean, 4),
            'IR': round(ir, 4),
            'IC Win Rate': f"{win_rate:.2%}",
            'G1 Return (x)': round(cum_returns.get('G1', 1.0), 2),
            'G5 Return (x)': round(cum_returns.get('G5', 1.0), 2),
            'Long-Short Spread': round(cum_returns.get('G5', 1.0) - cum_returns.get('G1', 1.0), 2)
        }

    def run_batch_evaluation(self, df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
        """运行所有因子的批量检验并输出汇总表"""
        print(f"\n开始批量检验 {len(factor_cols)} 个核心因子")
        results = []
        for i, factor in enumerate(factor_cols, 1):
            print(f"   [{i}/{len(factor_cols)}] 正在验证: {factor}")
            res = self.evaluate_single_factor(df, factor)
            results.append(res)
            
        return pd.DataFrame(results)


class FactorOrthogonalizer:
    """对称正交化引擎：剔除多因子间共线性干扰"""
    def __init__(self, min_stocks=3):
        self.min_stocks = min_stocks

    def process(self, df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
        print(f"\n实施对称正交化，优化信息结构，处理因子数: {len(factor_cols)}...")
        df_orth = df.copy()
        
        def symmetric_orth(group):
            if len(group) < self.min_stocks:
                for col in factor_cols:
                    group[col] = np.nan
                return group
                
            F = group[factor_cols].values
            F = np.nan_to_num(F)
            N = F.shape[0]
            if N == 0: return group
            
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


class StatisticalSelector:
    """统计学习特征筛选：基于 Lasso 识别稳定解释能力的核心因子"""
    @staticmethod
    def select_factors(df: pd.DataFrame, factor_cols: list, target='ret_next_month') -> list:
        print("\n执行 LassoCV 统计学习筛选，剥离无明显 Alpha 的冗余因子...")
        df_valid = df.dropna(subset=factor_cols + [target]).copy()
        df_valid = df_valid[(df_valid[target] >= -0.5) & (df_valid[target] <= 2.0)]
        
        if df_valid.empty:
            return factor_cols
            
        X, y = df_valid[factor_cols], df_valid[target]
        
        # 【核心修复4】：动态调整 LassoCV 的折数，以适应小样本池
        cv_folds = min(5, len(df_valid) // 2)
        if cv_folds < 2:
            return factor_cols
            
        try:
            lasso = LassoCV(cv=cv_folds, random_state=42, n_jobs=-1)
            lasso.fit(X, y)
            importance = pd.Series(np.abs(lasso.coef_), index=factor_cols)
            selected = importance[importance > 1e-6].sort_values(ascending=False).index.tolist()
            print(f"Lasso 筛选完毕。原始因子数: {len(factor_cols)} -> 保留核心因子数: {len(selected)}")
            return selected if selected else factor_cols
        except Exception as e:
            return factor_cols


class HeterogeneityAnalyzer:
    """异质性研究：分析因子在不同市场环境/行业下的表现"""
    @staticmethod
    def analyze(df: pd.DataFrame, factor: str, group_col: str, target='ret_next_month'):
        df_valid = df.dropna(subset=[factor, target, group_col]).copy()
        df_valid = df_valid[(df_valid[target] >= -0.5) & (df_valid[target] <= 2.0)]
        
        if df_valid.empty:
            return pd.DataFrame()
            
        def calc_ic(group):
            # 同样放宽异质性分析的门槛要求
            if len(group) >= 3 and group[factor].nunique() > 1 and group[target].nunique() > 1:
                ic, _ = st.spearmanr(group[factor], group[target])
                return ic
            return np.nan
            
        ic_panel = df_valid.groupby(['date', group_col]).apply(calc_ic).reset_index(name='IC')
        
        stats = ic_panel.groupby(group_col)['IC'].agg(
            IC_Mean='mean', IC_Std='std'
        )
        stats['IR'] = stats['IC_Mean'] / stats['IC_Std']
        stats['Win_Rate'] = ic_panel.groupby(group_col).apply(lambda x: (x['IC'] > 0).mean())
        
        return stats.fillna(0).round(4)