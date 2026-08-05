import numpy as np
import pandas as pd
import statsmodels.api as sm
from tqdm import tqdm
import warnings

# 忽略 statsmodels 某些极端情况下的多重共线性警告
warnings.filterwarnings("ignore")

class FactorProcessor:
    """
    底层单因子截面清洗引擎
    """
    def __init__(self, mad_multiplier=3.0):
        self.n = mad_multiplier
        self.mad_scale = 1.4826

    def fill_na_by_industry(self, factor, industry):
        df = pd.DataFrame({'factor': factor, 'industry': industry})
        ind_median = df.groupby('industry')['factor'].transform('median')
        return df['factor'].fillna(ind_median)

    def mad_winsorize(self, factor):
        median = factor.median()
        mad = (factor - median).abs().median()
        upper_limit = median + self.n * self.mad_scale * mad
        lower_limit = median - self.n * self.mad_scale * mad
        return factor.clip(lower=lower_limit, upper=upper_limit)

    def standardize(self, factor):
        mean = factor.mean()
        std = factor.std()
        return (factor - mean) / std if std != 0 else factor - mean

    def neutralize(self, factor, mcap, industry):
        ln_mcap = np.log(mcap.astype(float))
        ind_dummies = pd.get_dummies(industry, prefix='Ind', drop_first=True)
        X = pd.concat([ln_mcap, ind_dummies], axis=1)
        X = sm.add_constant(X)
        
        df = pd.concat([factor.rename('Y'), X], axis=1).dropna()
        if df.empty or len(df) < 3:
            return factor
            
        model = sm.OLS(df['Y'], df.drop(columns=['Y']))
        results = model.fit()
        return results.resid.reindex(factor.index)

    def process_pipeline(self, factor, mcap, industry):
        """标准五步走清洗流水线"""
        f1 = self.fill_na_by_industry(factor, industry)
        f2 = self.mad_winsorize(f1)
        f3 = self.standardize(f2)
        f4 = self.neutralize(f3, mcap, industry)
        f5 = self.standardize(f4)
        return f5


class MultiFactorPipeline:
    """
    全量多因子批处理外壳
    """
    def __init__(self, processor: FactorProcessor):
        self.processor = processor

    def run_batch_neutralization(self, df: pd.DataFrame, factor_cols: list) -> pd.DataFrame:
        print(f"【系统】准备执行全市场横截面中性化，共计 {len(factor_cols)} 个因子...")
        
        if 'mcap' not in df.columns or 'industry' not in df.columns:
            raise ValueError("数据框中缺失必备的中性化基准列：'mcap' 或 'industry'")

        clean_panel_list = []
        grouped = df.groupby(level='date')
        
        # tqdm 用于在控制台打印优美的进度条
        for date, daily_df in tqdm(grouped, desc="处理交易日横截面"):
            if len(daily_df) < 3: # 样本过少则跳过当天
                continue
                
            daily_data = daily_df.reset_index(level='date', drop=True)
            daily_clean_dict = {}
            
            mcap = daily_data['mcap']
            industry = daily_data['industry']
            
            # 循环清洗当日的所有指定因子
            for factor_name in factor_cols:
                raw_factor = daily_data[factor_name]
                
                if raw_factor.count() < 3:
                    daily_clean_dict[factor_name] = pd.Series(np.nan, index=daily_data.index)
                    continue
                
                clean_factor = self.processor.process_pipeline(
                    factor=raw_factor,
                    mcap=mcap,
                    industry=industry
                )
                daily_clean_dict[factor_name] = clean_factor
            
            daily_res_df = pd.DataFrame(daily_clean_dict)
            daily_res_df['date'] = date
            clean_panel_list.append(daily_res_df)

        print("\n【系统】正在重组全量纯净面板数据...")
        final_clean_df = pd.concat(clean_panel_list)
        final_clean_df = final_clean_df.set_index('date', append=True).swaplevel().sort_index()
        
        return final_clean_df