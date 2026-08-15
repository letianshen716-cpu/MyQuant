"""
Data Validator Module (数据质量校验引擎)
检测基础数据覆盖度、缺失率与离群点
"""

import pandas as pd
import numpy as np

class DataValidator:
    """自动化样本质量与偏差识别模块"""

    @staticmethod
    def check_missing_values(df: pd.DataFrame) -> pd.DataFrame:
        """扫视全表字段，统计并输出缺失率大于0的特征"""
        if df.empty:
            return pd.DataFrame()
            
        missing_ratio = df.isnull().mean() * 100
        report = pd.DataFrame({'Missing_Ratio_Pct': missing_ratio})
        return report[report['Missing_Ratio_Pct'] > 0]

    @staticmethod
    def identify_extreme_outliers(df: pd.DataFrame, column: str, z_thresh: float = 4.0) -> pd.DataFrame:
        """利用 Z-score 识别极端分布异象（错漏数据、未复权跳空等）"""
        if column not in df.columns or df.empty:
            return pd.DataFrame()
            
        series = df[column].dropna()
        if series.empty:
            return pd.DataFrame()
            
        z_scores = (series - series.mean()) / (series.std() + 1e-8)
        outlier_mask = np.abs(z_scores) > z_thresh
        return df.loc[outlier_mask.index[outlier_mask]]