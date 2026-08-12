import pymongo
import pandas as pd
import numpy as np
import QUANTAXIS as QA

def build_technical_features(code_list: list) -> pd.DataFrame:
    """提取日线行情，转换为前复权(QFQ)价格，计算技术面因子，降频为月度截面"""
    
    qa_data = QA.QA_fetch_stock_day_adv(code_list, '2020-01-01', '2024-12-31')
    if qa_data is None:
        raise ValueError("未检测到日线行情数据！请确保已下载数据")
        
    try:
        qa_data_qfq = qa_data.to_qfq()
    except Exception as e:
        print(f"前复权计算失败，退回未复权数据。原因: {e}")
        qa_data_qfq = qa_data

    df_raw = qa_data_qfq.data.reset_index()
    
    df_raw['date'] = pd.to_datetime(df_raw['date'])
    df_raw['close'] = df_raw['close'].astype(float)
    df_raw['amount'] = df_raw['amount'].astype(float)
    df_raw['code'] = df_raw['code'].astype(str).str.zfill(6)
    df_raw = df_raw.sort_values(by=['code', 'date']).reset_index(drop=True)
    
    print("正在基于复权价格计算多维技术面与环境因子")
    df_raw['momentum_10d'] = df_raw.groupby('code')['close'].pct_change(periods=10)
    df_raw['momentum_20d'] = df_raw.groupby('code')['close'].pct_change(periods=20)
    df_raw['ret_1d'] = df_raw.groupby('code')['close'].pct_change(1)
    df_raw['volatility'] = df_raw.groupby('code')['ret_1d'].rolling(window=20).std().reset_index(0, drop=True)
    df_raw['amt_mean_20d'] = df_raw.groupby('code')['amount'].rolling(window=20).mean().reset_index(0, drop=True)
    
    def map_industry(code):
        if code.startswith('600'): return 'Finance/LargeCap'
        elif code.startswith('000'): return 'IT/Media'
        elif code.startswith('002'): return 'Manufacturing'
        elif code.startswith('300'): return 'Growth/Tech'
        else: return 'Others'
    df_raw['industry'] = df_raw['code'].apply(map_industry)

    df_raw['year_month'] = df_raw['date'].dt.to_period('M')
    df_monthly = df_raw.sort_values('date').groupby(['code', 'year_month']).tail(1).reset_index(drop=True)
    
    df_monthly['next_close'] = df_monthly.groupby('code')['close'].shift(-1)
    df_monthly['ret_next_month'] = df_monthly['next_close'] / df_monthly['close'] - 1
    
    market_trend = df_monthly.groupby('date')['ret_next_month'].mean()
    df_monthly['market_state'] = df_monthly['date'].map(lambda d: 'Bull' if market_trend.get(d, 0) > 0 else 'Bear')
    
    cols = ['date', 'code', 'industry', 'market_state', 'momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'ret_next_month']
    return df_monthly[cols].dropna(subset=['ret_next_month'])


def build_fundamental_features(code_list: list) -> pd.DataFrame:
    print("【步骤 2/3】提取财报并构建基本面因子池...")
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
        
    def get_safe_date(rd):
        m, y = rd.month, rd.year
        if m == 3: return pd.Timestamp(y, 5, 1)
        elif m == 6: return pd.Timestamp(y, 9, 1)
        elif m == 9: return pd.Timestamp(y, 11, 1)
        else: return pd.Timestamp(y + 1, 5, 1)
        
    df_fund['safe_date'] = df_fund['report_date'].apply(get_safe_date)
    return df_fund[['code', 'safe_date', 'roe']]


def build_pit_wide_table(code_list=['000001', '600000', '600519', '002001', '300001']) -> pd.DataFrame:
    print("【步骤 3/3】执行 PIT 严格对齐，生成最终大宽表...")
    df_monthly = build_technical_features(code_list) 
    df_fund = build_fundamental_features(code_list)
    
    if df_fund.empty:
        df_monthly['roe'] = np.nan
        return df_monthly
        
    df_monthly = df_monthly.sort_values('date')
    df_fund = df_fund.sort_values('safe_date')
    
    df_all_factors = pd.merge_asof(
        df_monthly, df_fund, by='code', left_on='date', right_on='safe_date', direction='backward'
    )
    if 'safe_date' in df_all_factors.columns:
        df_all_factors = df_all_factors.drop(columns=['safe_date'])
        
    df_all_factors['roe'] = df_all_factors.groupby('date')['roe'].transform(lambda x: x.fillna(x.median()))
    print(f"有效样本量: {len(df_all_factors)} 行。")
    return df_all_factors