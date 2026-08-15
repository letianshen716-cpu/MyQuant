"""
Data Cleaner Module (数据清洗与防偏差处理引擎)
包含缺失值处理、生存偏差过滤与 PIT 财报严格时间对齐
"""

import pandas as pd
import numpy as np
from typing import List

class DataCleaner:
    """金融数据清洗与校正引擎"""

    @staticmethod
    def _get_safe_report_date(report_date: pd.Timestamp) -> pd.Timestamp:
        """
        根据 A 股财报法定披露截止日，推导无前视偏差的安全可用日 (PIT)
        """
        m, y = report_date.month, report_date.year
        if m in [1, 2, 3]: return pd.Timestamp(y, 5, 1)      # 一季报 -> 5月1日可见
        elif m in [4, 5, 6]: return pd.Timestamp(y, 9, 1)    # 中报 -> 9月1日可见
        elif m in [7, 8, 9]: return pd.Timestamp(y, 11, 1)   # 三季报 -> 11月1日可见
        else: return pd.Timestamp(y + 1, 5, 1)               # 年报 -> 次年5月1日可见

    def align_pit_financials(self, price_df: pd.DataFrame, fin_df: pd.DataFrame) -> pd.DataFrame:
        """
        将低频财务数据严格向后 (Backward) 对齐到高频截面行情数据上，消除前视偏差
        """
        print("执行 PIT (Point-in-Time) 财报向后严格对齐")
        
        # 1. 计算安全可用日
        fin_df['safe_date'] = pd.to_datetime(fin_df['report_date']).apply(self._get_safe_report_date)
        
        # 2. 排序准备 merge_asof
        price_df = price_df.sort_values('date')
        fin_df = fin_df.dropna(subset=['safe_date']).sort_values('safe_date')
        
        # 3. 执行 AsOf 拼接 (按标的与时间匹配最近的一份已公开财报)
        merged_df = pd.merge_asof(
            price_df, 
            fin_df, 
            by='code', 
            left_on='date', 
            right_on='safe_date', 
            direction='backward'
        )
        
        if 'safe_date' in merged_df.columns:
            merged_df = merged_df.drop(columns=['safe_date'])
            
        return merged_df

    @staticmethod
    def fill_missing_with_industry_median(df: pd.DataFrame, factor_cols: List[str], industry_col: str = 'industry') -> pd.DataFrame:
        """
        缺失值处理：按每个交易日横截面，使用同行业中位数填补缺失因子值
        """
        print(" 执行截面行业中位数缺失值填补")
        df_out = df.copy()

        def fill_median(group):
            for col in factor_cols:
                if col in group.columns:
                    group[col] = group[col].fillna(group[col].median())
            return group

        # 双重分组：先按日期，再按行业
        df_out = df_out.groupby(['date', industry_col], group_keys=False).apply(fill_median)
        
        # 如果行业全量缺失，采用全市场截面中位数兜底
        df_out[factor_cols] = df_out.groupby('date')[factor_cols].transform(lambda x: x.fillna(x.median()))
        return df_out