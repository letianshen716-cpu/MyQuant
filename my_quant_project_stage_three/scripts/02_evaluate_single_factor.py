import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import pymongo
import pandas as pd
import numpy as np
import scipy.stats as st
from config import MONGO_URI, FACTOR_ALL_HISTORY_PATH, MONTHLY_FRICTION_COST

def run_monthly_realistic_evaluation():
    print("正在加载全量历史因子数据...")
    df_factor = pd.read_csv(FACTOR_ALL_HISTORY_PATH, dtype={'code': str})
    df_factor['code'] = df_factor['code'].astype(str).str.zfill(6)
    df_factor['date'] = pd.to_datetime(df_factor['date'])
    
    start_date = df_factor['date'].min()

    print("提取底层行情，计算月度收益...")
    client = pymongo.MongoClient(MONGO_URI)
    collection = client['quantaxis']['stock_day']
    
    cursor = collection.find({'date': {'$gte': start_date.strftime('%Y-%m-%d')}}, {'_id': 0, 'date': 1, 'code': 1, 'close': 1})
    df_price = pd.DataFrame(list(cursor))
    df_price['date'] = pd.to_datetime(df_price['date'])
    df_price['close'] = df_price['close'].astype(float)
    df_price['code'] = df_price['code'].astype(str).str.zfill(6)
    
    df_merge = pd.merge(df_factor, df_price, on=['date', 'code'], how='inner')
    df_merge['year_month'] = df_merge['date'].dt.to_period('M')
    
    # 截取每月最后一天调仓
    df_monthly = df_merge.sort_values('date').groupby(['code', 'year_month']).tail(1).reset_index(drop=True)
    df_monthly['next_month_close'] = df_monthly.groupby('code')['close'].shift(-1)
    df_monthly['ret_next_month'] = df_monthly['next_month_close'] / df_monthly['close'] - 1
    df_monthly = df_monthly.dropna(subset=['ret_next_month'])

    # 极端值清洗 (防止除权异动)
    valid_mask = (
        (df_monthly['factor_value'] > -0.4) & (df_monthly['factor_value'] < 1.0) &
        (df_monthly['ret_next_month'] > -0.4) & (df_monthly['ret_next_month'] < 1.0)
    )
    df_monthly = df_monthly[valid_mask].copy()

    # 计算 Rank IC 与 IR
    def calc_ic(group):
        if len(group) > 30:
            ic, _ = st.spearmanr(group['factor_value'], group['ret_next_month'])
            return ic
        return np.nan

    ic_series = df_monthly.groupby('date').apply(calc_ic).dropna()
    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    ir = ic_mean / ic_std if ic_std != 0 else 0
    
    print("=" * 40)
    print(f"真实月度 Rank IC 均值: {ic_mean:.4f}")
    print(f"真实月度 IR 比率:     {ir:.4f}")
    print(f"月度胜率:            {(ic_series < 0).mean():.2%} (反转因子: IC<0 胜率)")
    print("=" * 40)

    # 分组累积收益 (扣除摩擦成本)
    def get_quantiles(group):
        if len(group) < 30:
            return pd.Series(float('nan'), index=group.index)
        labels = ['Group_1', 'Group_2', 'Group_3', 'Group_4', 'Group_5']
        return pd.qcut(group['factor_value'].rank(method='first'), q=5, labels=labels)

    df_monthly['group'] = df_monthly.groupby('date', group_keys=False).apply(get_quantiles)
    monthly_returns = df_monthly.groupby(['date', 'group'])['ret_next_month'].mean().unstack()
    
    monthly_returns_net = monthly_returns - MONTHLY_FRICTION_COST
    cumulative_returns = (1 + monthly_returns_net).cumprod()
    
    print("\n扣除交易成本后，各分组最终真实累积收益 (倍数):")
    print(cumulative_returns.iloc[-1].round(2))

if __name__ == '__main__':
    run_monthly_realistic_evaluation()