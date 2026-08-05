import sys
from pathlib import Path

# 将项目根目录加入系统路径
sys.path.append(str(Path(__file__).parent.parent))

import ssl
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA
import pandas as pd
import numpy as np

# 导入全局配置和刚才封装好的工具类
from config import FACTOR_STOCKS, FACTOR_START_DATE, FACTOR_END_DATE, MAD_MULTIPLIER
from utils.factor_tools import FactorProcessor, MultiFactorPipeline
from utils.factor_db import FactorDatabase

def run_batch_research():
    print("正在从 MongoDB 拉取量价数据")
    
    qa_data = QA.QA_fetch_stock_day_adv(FACTOR_STOCKS, FACTOR_START_DATE, FACTOR_END_DATE)
    if qa_data is None:
        print("数据库无数据！")
        return

    # 前复权转换
    df = qa_data.to_qfq().data.copy()
    print(f"数据拉取成功！共包含 {len(df)} 条日线记录。")

    print("正在计算多个原始因子")

    
    # 因子1：20日动量
    df['mom_20'] = df['close'].groupby(level='code').pct_change(20)
    # 因子2：5日平均量
    df['vol_mean_5'] = df['volume'].groupby(level='code').transform(lambda x: x.rolling(5).mean())
    # 因子3：20日波动率
    df['pct_chg'] = df['close'].groupby(level='code').pct_change()
    df['volatility_20'] = df['pct_chg'].groupby(level='code').transform(lambda x: x.rolling(20).std())

    df = df.dropna(subset=['mom_20', 'vol_mean_5', 'volatility_20']).copy()

    print("拼接财务数据 (市值与行业) 并执行全量清洗")

    
    # 模拟财务数据
    np.random.seed(42)
    df['mcap'] = np.random.uniform(100, 10000, size=len(df))
    industries = ['Bank', 'RealEstate', 'Tech', 'Liquor', 'Auto']
    df['industry'] = np.random.choice(industries, size=len(df))

    # 初始化批处理引擎
    processor = FactorProcessor(mad_multiplier=MAD_MULTIPLIER)
    batch_pipeline = MultiFactorPipeline(processor=processor)
    target_factors = ['mom_20', 'vol_mean_5', 'volatility_20']

    # 执行批处理
    clean_factors_df = batch_pipeline.run_batch_neutralization(
        df=df,
        factor_cols=target_factors
    )

    print("4. 正在将各因子独立拆分，写入 FactorDatabase")

    
    db = FactorDatabase()
    
    for factor_name in target_factors:
        single_factor_df = clean_factors_df[[factor_name]].copy()
        single_factor_df = single_factor_df.rename(columns={factor_name: 'value'})
        single_factor_df = single_factor_df.reset_index()
        
        if 'code' in single_factor_df.columns:
            single_factor_df = single_factor_df.rename(columns={'code': 'ticker'})
            
        db.save_factor(
            df=single_factor_df, 
            factor_name=factor_name, 
            version="v1.0",
            description=f"自动批处理生成：{factor_name}"
        )
        
    print("\n多因子批处理及入库全部完成！")

if __name__ == '__main__':
    run_batch_research()