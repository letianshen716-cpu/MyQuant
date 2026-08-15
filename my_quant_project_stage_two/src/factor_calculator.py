"""
Factor Calculator Module (因子计算引擎 - 扩展版)
提供基本面、技术面、另类三大维度，共计 20+ 核心因子的底层计算逻辑
"""

import pandas as pd
import numpy as np

class FactorCalculator:
    
    @staticmethod
    def calculate_technical_factors(df: pd.DataFrame, price_col: str = 'close', vol_col: str = 'volume') -> pd.DataFrame:
        """
        计算常用技术面因子 (动量、波动率、流动性等共 10 个)
        """
        df_out = df.copy()
        print(">>> [因子计算] 正在计算技术面因子 (10个)...")
        
        # 1. 动量因子
        df_out['mom_10d'] = df_out.groupby('code')[price_col].pct_change(periods=10)
        df_out['mom_20d'] = df_out.groupby('code')[price_col].pct_change(periods=20)
        df_out['ret_1d'] = df_out.groupby('code')[price_col].pct_change(periods=1)
        
        # 2. 波动率与流动性
        df_out['volatility_20d'] = df_out.groupby('code')['ret_1d'].rolling(window=20).std().reset_index(0, drop=True)
        df_out['volume_mean_20d'] = df_out.groupby('code')[vol_col].rolling(window=20).mean().reset_index(0, drop=True)
        
        # 3. 极值动量
        df_out['max_ret_5d'] = df_out.groupby('code')['ret_1d'].rolling(window=5).max().reset_index(0, drop=True)
        df_out['min_ret_5d'] = df_out.groupby('code')['ret_1d'].rolling(window=5).min().reset_index(0, drop=True)
        
        # 4. Amihud 非流动性因子
        df_out['amihud_20d'] = df_out.groupby('code').apply(
            lambda x: (x['ret_1d'].abs() / (x[vol_col] + 1e-8)).rolling(window=20).mean()
        ).reset_index(level=0, drop=True)
        
        # 5. 简单移动平均线乖离率 (Bias)
        df_out['sma_20d'] = df_out.groupby('code')[price_col].rolling(window=20).mean().reset_index(0, drop=True)
        df_out['bias_20d'] = (df_out[price_col] - df_out['sma_20d']) / (df_out['sma_20d'] + 1e-8)
        
        # 6. 成交量波动率
        df_out['vol_var_20d'] = df_out.groupby('code')[vol_col].rolling(window=20).std().reset_index(0, drop=True)
        
        # 清理过程辅助列
        df_out = df_out.drop(columns=['ret_1d', 'sma_20d'])
        return df_out

    @staticmethod
    def calculate_fundamental_factors(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算衍生基本面因子 (盈利能力、估值、杠杆等共 7 个)
        """
        df_out = df.copy()
        print(">>> [因子计算] 正在计算基本面因子 (7个)...")
        
        # 防止除以 0 的极小值底数
        epsilon = 1e-8
        
        # 1. 核心盈利与估值
        if 'net_profit' in df_out.columns and 'total_equity' in df_out.columns:
            df_out['roe'] = df_out['net_profit'] / (df_out['total_equity'] + epsilon)
        if 'net_profit' in df_out.columns and 'market_cap' in df_out.columns:
            df_out['ep'] = df_out['net_profit'] / (df_out['market_cap'] + epsilon)
            
        # 2. 资产周转与回报
        if 'total_assets' in df_out.columns:
            df_out['roa'] = df_out['net_profit'] / (df_out['total_assets'] + epsilon) 
            df_out['asset_turnover'] = df_out.get('operating_revenue', pd.Series(0, index=df_out.index)) / (df_out['total_assets'] + epsilon) 
            
        # 3. 杠杆与风险
        if 'total_liabilities' in df_out.columns and 'total_equity' in df_out.columns:
            df_out['debt_to_equity'] = df_out['total_liabilities'] / (df_out['total_equity'] + epsilon)
            
        # 4. 利润率与现金流质量
        if 'operating_revenue' in df_out.columns and 'operating_cost' in df_out.columns:
            df_out['gross_margin'] = (df_out['operating_revenue'] - df_out['operating_cost']) / (df_out['operating_revenue'] + epsilon)
            
        if 'operating_cash_flow' in df_out.columns and 'net_profit' in df_out.columns:
            df_out['ocf_to_ni'] = df_out['operating_cash_flow'] / (df_out['net_profit'].abs() + epsilon) 
            
        return df_out

    @staticmethod
    def calculate_alternative_factors(df: pd.DataFrame) -> pd.DataFrame:
        """
        计算另类与宏观衍生因子 (共 3 个)
        """
        df_out = df.copy()
        print(">>> [因子计算] 正在计算另类与宏观因子 (3个)...")
        
        # 1. 机构情绪异动因子 (大单净流入模拟：针对 60 日滚动均值的异常放量)
        df_out['inst_sentiment'] = df_out.groupby('code')['volume'].transform(
            lambda x: (x - x.rolling(60).mean()) / (x.rolling(60).std() + 1e-8)
        )
        
        # 2. 尾部风险 (Tail Risk) - 过去 20 天最大回撤比例
        df_out['tail_risk_20d'] = df_out.groupby('code')['close'].transform(
            lambda x: (x.rolling(20).min() - x.rolling(20).max()) / (x.rolling(20).max() + 1e-8)
        )
        
        # 3. 相对大盘 Beta 强度代理
        market_vol = df_out.groupby('date')['close'].transform(lambda x: x.pct_change().std())
        if 'volatility_20d' in df_out.columns:
            df_out['beta_proxy'] = df_out['volatility_20d'] / (market_vol + 1e-8)
        
        return df_out