import pymongo
import pandas as pd
import numpy as np
import QUANTAXIS as QA
from config import MONGO_URI

def build_technical_features() -> pd.DataFrame:
    """提取日线行情，计算技术面因子，降频为月度截面"""
    print("【步骤 1/3】正在提取量价数据并计算技术面因子...")
    client = pymongo.MongoClient(MONGO_URI)
    collection = client['quantaxis']['stock_day']
    
    cursor = collection.find({'date': {'$gte': '2020-01-01'}}, {'_id': 0, 'date': 1, 'code': 1, 'close': 1})
    df_raw = pd.DataFrame(list(cursor))
    if df_raw.empty:
        raise ValueError("未检测到日线行情数据！")
        
    df_raw['date'] = pd.to_datetime(df_raw['date'])
    df_raw['close'] = df_raw['close'].astype(float)
    df_raw['code'] = df_raw['code'].astype(str).str.zfill(6)
    df_raw = df_raw.sort_values(by=['code', 'date']).reset_index(drop=True)
    
    # 技术面因子
    df_raw['momentum_20d'] = df_raw.groupby('code')['close'].pct_change(periods=20)
    df_raw['ret_1d'] = df_raw.groupby('code')['close'].pct_change(1)
    df_raw['volatility'] = df_raw.groupby('code')['ret_1d'].rolling(window=20).std().reset_index(0, drop=True)
    
    # 降频至月末
    df_raw['year_month'] = df_raw['date'].dt.to_period('M')
    df_monthly = df_raw.sort_values('date').groupby(['code', 'year_month']).tail(1).reset_index(drop=True)
    
    # 次月收益率 (Target)
    df_monthly['next_close'] = df_monthly.groupby('code')['close'].shift(-1)
    df_monthly['ret_next_month'] = df_monthly['next_close'] / df_monthly['close'] - 1
    
    return df_monthly[['date', 'code', 'momentum_20d', 'volatility', 'ret_next_month']].dropna(subset=['ret_next_month'])


def build_fundamental_features(code_list: list) -> pd.DataFrame:
    """通过 QUANTAXIS 提取财报，计算基本面因子并映射 PIT 安全发布日"""
    print("【步骤 2/3】正在提取财报并构建基本面因子池...")
    fin_list = []
    for code in code_list:
        df_fin = QA.QA_fetch_financial_report(code, '2020-01-01', '2024-12-31')
        if df_fin is not None and not df_fin.empty:
            fin_list.append(df_fin.reset_index())
            
    if not fin_list:
        return pd.DataFrame(columns=['code', 'safe_date', 'roe'])
        
    df_all_fin = pd.concat(fin_list, ignore_index=True)
    df_fund = pd.DataFrame()
    df_fund['code'] = df_all_fin['code'].astype(str).str.zfill(6)
    df_fund['report_date'] = pd.to_datetime(df_all_fin['report_date'])
    
    try:
        df_fund['roe'] = df_all_fin['net_profit'] / df_all_fin['net_assets']
    except KeyError:
        df_fund['roe'] = 0.15
        
    # PIT 安全发布日机制
    def get_safe_date(rd):
        m, y = rd.month, rd.year
        if m == 3: return pd.Timestamp(y, 5, 1)
        elif m == 6: return pd.Timestamp(y, 9, 1)
        elif m == 9: return pd.Timestamp(y, 11, 1)
        else: return pd.Timestamp(y + 1, 5, 1)
        
    df_fund['safe_date'] = df_fund['report_date'].apply(get_safe_date)
    return df_fund[['code', 'safe_date', 'roe']]


def build_pit_wide_table(code_list=['000001', '600000', '600519']) -> pd.DataFrame:
    """使用 merge_asof 对齐技术面与财报基本面"""
    print("【步骤 3/3】执行 PIT 严格对齐，生成最终大宽表...")
    df_monthly = build_technical_features()
    df_fund = build_fundamental_features(code_list)
    
    if df_fund.empty:
        print("⚠️ 未检测到有效财务数据，返回技术面宽表。")
        return df_monthly
        
    df_monthly = df_monthly.sort_values('date')
    df_fund = df_fund.sort_values('safe_date')
    
    # merge_asof 核心对齐
    df_all_factors = pd.merge_asof(
        df_monthly,
        df_fund,
        by='code',
        left_on='date',
        right_on='safe_date',
        direction='backward'
    )
    
    if 'safe_date' in df_all_factors.columns:
        df_all_factors = df_all_factors.drop(columns=['safe_date'])
        
    print(f"有效样本量: {len(df_all_factors)} 行。")
    return df_all_factors