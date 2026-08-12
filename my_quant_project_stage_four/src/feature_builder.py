"""
Feature Builder Module (多维特征与 PIT 大宽表构建引擎)
支持分批加载复权行情、自适应解析板块映射及 PIT 财报向后无偏对齐
"""

import gc
import ssl
from typing import List, Optional
import numpy as np
import pandas as pd
import QUANTAXIS as QA

# 全局注入 SSL 补丁
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()


def build_technical_features(code_list: List[str], batch_size: int = 300) -> pd.DataFrame:
    """分批提取日线行情并复权，计算技术面量价因子，降频为月度截面"""
    print(f"【步骤 1/3】分批提取前复权 (QFQ) 量价数据 (共 {len(code_list)} 只股票，批次大小: {batch_size})")

    # 1. 自动探测板块集合并解析
    print("   -> 正在多集合自动探测并展开行业板块映射...")
    industry_map = {}
    try:
        target_colls = ['stock_block', 'stock_block_tdx', 'stock_block_ths']
        for cname in target_colls:
            if cname in QA.DATABASE.list_collection_names():
                cursor = QA.DATABASE[cname].find({}, {'_id': 0, 'code': 1, 'blockname': 1})
                for doc in cursor:
                    bname = doc.get('blockname', '')
                    codes = doc.get('code', [])
                    if isinstance(codes, list):
                        for c in codes:
                            industry_map[str(c).zfill(6)] = bname
                    elif isinstance(codes, (str, int)):
                        industry_map[str(codes).zfill(6)] = bname
                if industry_map:
                    break

        if industry_map:
            print(f"   ->  成功载入并匹配 {len(industry_map)} 只股票的行业板块分类数据！")
        else:
            print(" 未在数据库探测到已存储的板块数据，启用代码前缀降级策略。")
    except Exception as e:
        print(f" 读取板块数据失败，原因: {e}，启用代码前缀降级策略。")

    def map_industry_accurate(code: str) -> str:
        clean_code = str(code).zfill(6)
        block_name = industry_map.get(clean_code, '未分类')

        if any(kw in block_name for kw in ['银行', '证券', '保险', '多元金融', '信托', '金融']):
            return 'Finance/LargeCap'
        elif any(kw in block_name for kw in ['软件', '计算机', '通信', '传媒', '半导体', 'IT', '电子', '互联网']):
            return 'IT/Media'
        elif any(kw in block_name for kw in ['机械', '设备', '汽车', '化工', '钢铁', '制造', '电力', '军工', '建材']):
            return 'Manufacturing'
        elif block_name != '未分类':
            return 'Others'
        else:
            if clean_code.startswith(('601', '000001')):
                return 'Finance/LargeCap'
            elif clean_code.startswith(('300', '688')):
                return 'Growth/Tech'
            else:
                return 'Others'

    # 2. 分批拉取与因子滚动计算
    all_monthly_chunks = []
    total_batches = (len(code_list) + batch_size - 1) // batch_size

    for idx in range(0, len(code_list), batch_size):
        chunk_codes = code_list[idx : idx + batch_size]
        curr_batch = idx // batch_size + 1
        print(f"   -> 正在处理批次 [{curr_batch}/{total_batches}] ({len(chunk_codes)} 只股票)")

        try:
            qa_data = QA.QA_fetch_stock_day_adv(chunk_codes, '2020-01-01', '2026-12-31')
            if qa_data is None:
                continue
            try:
                qa_data_qfq = qa_data.to_qfq()
            except Exception:
                qa_data_qfq = qa_data

            df_raw = qa_data_qfq.data.reset_index()
        except Exception as e:
            print(f"  批次 [{curr_batch}] 提取异常，已跳过: {e}")
            continue

        if df_raw.empty:
            continue

        df_raw['date'] = pd.to_datetime(df_raw['date'])
        df_raw['close'] = df_raw['close'].astype(float)
        df_raw['amount'] = df_raw['amount'].astype(float)
        df_raw['code'] = df_raw['code'].astype(str).str.zfill(6)
        df_raw = df_raw.sort_values(by=['code', 'date']).reset_index(drop=True)

        # 量价技术因子
        df_raw['momentum_10d'] = df_raw.groupby('code')['close'].pct_change(periods=10)
        df_raw['momentum_20d'] = df_raw.groupby('code')['close'].pct_change(periods=20)
        df_raw['ret_1d'] = df_raw.groupby('code')['close'].pct_change(1)
        df_raw['volatility'] = df_raw.groupby('code')['ret_1d'].rolling(window=20).std().reset_index(0, drop=True)
        df_raw['amt_mean_20d'] = df_raw.groupby('code')['amount'].rolling(window=20).mean().reset_index(0, drop=True)
        df_raw['industry'] = df_raw['code'].apply(map_industry_accurate)

        # 降频为月度截面
        df_raw['year_month'] = df_raw['date'].dt.to_period('M')
        df_monthly_chunk = df_raw.sort_values('date').groupby(['code', 'year_month']).tail(1).reset_index(drop=True)

        df_monthly_chunk['next_close'] = df_monthly_chunk.groupby('code')['close'].shift(-1)
        df_monthly_chunk['ret_next_month'] = df_monthly_chunk['next_close'] / df_monthly_chunk['close'] - 1.0

        cols = ['date', 'code', 'industry', 'momentum_10d', 'momentum_20d', 'volatility', 'amt_mean_20d', 'ret_next_month']
        all_monthly_chunks.append(df_monthly_chunk[cols].dropna(subset=['ret_next_month']))

        del df_raw, df_monthly_chunk
        gc.collect()

    if not all_monthly_chunks:
        raise ValueError("未能提取到任何有效量价数据，请检查 MongoDB 数据库。")

    df_monthly = pd.concat(all_monthly_chunks, ignore_index=True)
    market_trend = df_monthly.groupby('date')['ret_next_month'].mean()
    df_monthly['market_state'] = df_monthly['date'].map(lambda d: 'Bull' if market_trend.get(d, 0) > 0 else 'Bear')

    return df_monthly


def build_fundamental_features(code_list: list, batch_size: int = 500) -> pd.DataFrame:
    """自适应探测字段并分批拉取财务数据，避免内存溢出与断连"""
    print(f"【步骤 2/3】正在从数据库分批加载全市场财报数据 (批次大小: {batch_size})...")

    coll = QA.DATABASE.financial
    
    # 1. 探针：获取一条最新记录以确定真实的底层字段名，避免全量提取 300+ 个无用字段撑爆内存
    sample_doc = coll.find_one({'report_date': {'$gte': '2020-01-01'}})
    if not sample_doc:
        sample_doc = coll.find_one() # 降级探测
        
    if not sample_doc:
        print("⚠️ 数据库 financial 集合完全为空！请确认是否成功执行了下载。")
        return pd.DataFrame(columns=['code', 'safe_date', 'roe'])

    profit_candidates = ['净利润', '归属于母公司所有者的净利润', '归属于母公司股东的净利润', '归母净利润', 'net_profit', 'netProfit']
    asset_candidates = ['净资产', '所有者权益合计', '归属于母公司所有者权益合计', '所有者权益(或股东权益)合计', '股东权益合计', 'net_assets', 'total_equity', 'netAssets']
    roe_candidates = ['roe', 'ROE', '净资产收益率', '加权平均净资产收益率']

    profit_col = next((c for c in profit_candidates if c in sample_doc), None)
    asset_col = next((c for c in asset_candidates if c in sample_doc), None)
    roe_col = next((c for c in roe_candidates if c in sample_doc), None)

    # 构建轻量化投影字典 (只加载必须的 4 个字段)
    projection = {'_id': 0, 'code': 1, 'report_date': 1}
    if profit_col: projection[profit_col] = 1
    if asset_col: projection[asset_col] = 1
    if roe_col: projection[roe_col] = 1

    print(f"   -> 探测到财报底层字段，启用轻量化提取投影: {list(projection.keys())}")

    fin_records = []
    total_batches = (len(code_list) + batch_size - 1) // batch_size
    
    from datetime import datetime
    
    # 2. 分批按代码拉取，防范 BSON Size Limit 与 MemoryError
    for idx in range(0, len(code_list), batch_size):
        chunk_codes = code_list[idx : idx + batch_size]
        curr_batch = idx // batch_size + 1
        
        try:
            # 兼容多种格式的时间筛选
            cursor = coll.find(
                {
                    'code': {'$in': chunk_codes},
                    '$or': [
                        {'report_date': {'$gte': '2020-01-01'}},
                        {'report_date': {'$gte': 20200101}},
                        {'report_date': {'$gte': datetime(2020, 1, 1)}}
                    ]
                },
                projection
            )
            fin_records.extend(list(cursor))
        except Exception as e:
            print(f"  批次 [{curr_batch}] 读取财务数据异常，已跳过: {e}")

    if not fin_records:
        print(" 未检索到 2020 年以后的财务记录！")
        return pd.DataFrame(columns=['code', 'safe_date', 'roe'])

    df_all_fin = pd.DataFrame(fin_records)
    print(f"   -> 成功批量获取 {len(df_all_fin)} 条财报数据，正在计算 ROE 并对齐 PIT 时间点...")

    df_fund = pd.DataFrame()
    df_fund['code'] = df_all_fin['code'].astype(str).str.zfill(6)
    df_fund['report_date'] = pd.to_datetime(df_all_fin['report_date'].astype(str))

    if roe_col is not None and roe_col in df_all_fin.columns:
        df_fund['roe'] = pd.to_numeric(df_all_fin[roe_col], errors='coerce')
    elif profit_col is not None and asset_col is not None and profit_col in df_all_fin.columns and asset_col in df_all_fin.columns:
        p = pd.to_numeric(df_all_fin[profit_col], errors='coerce')
        a = pd.to_numeric(df_all_fin[asset_col], errors='coerce')
        df_fund['roe'] = p / a
    else:
        df_fund['roe'] = 0.08 # 默认兜底

    df_fund['roe'] = df_fund['roe'].replace([np.inf, -np.inf], np.nan)
    valid_roe = df_fund['roe'].dropna()
    if not valid_roe.empty and valid_roe.abs().median() > 1.0:
        df_fund['roe'] = df_fund['roe'] / 100.0

    def get_safe_date(rd: pd.Timestamp) -> pd.Timestamp:
        m, y = rd.month, rd.year
        if m in [1, 2, 3]: return pd.Timestamp(y, 5, 1)      
        elif m in [4, 5, 6]: return pd.Timestamp(y, 9, 1)    
        elif m in [7, 8, 9]: return pd.Timestamp(y, 11, 1)   
        else: return pd.Timestamp(y + 1, 5, 1)               

    df_fund['safe_date'] = df_fund['report_date'].apply(get_safe_date)
    df_fund = df_fund.dropna(subset=['roe']).sort_values('report_date').drop_duplicates(subset=['code', 'safe_date'], keep='last')
    print(f"   -> 有效 ROE 基本面记录: {len(df_fund)} 条")
    return df_fund[['code', 'safe_date', 'roe']]


def build_pit_wide_table(code_list: Optional[List[str]] = None) -> pd.DataFrame:
    """执行 PIT 严格向后对齐，生成全量因子大宽表"""
    if code_list is None:
        code_list = QA.DATABASE.stock_day.distinct('code')

    print(f"【步骤 3/3】准备处理 {len(code_list)} 只股票，执行 PIT 严格对齐")
    df_monthly = build_technical_features(code_list, batch_size=300)
    df_fund = build_fundamental_features(code_list)

    if df_fund.empty:
        print("财务数据计算为空，ROE 将自动填充为空值！")
        df_monthly['roe'] = np.nan
        return df_monthly

    df_monthly = df_monthly.sort_values('date')
    df_fund = df_fund.sort_values('safe_date')

    # Merge AsOf PIT 向后匹配
    df_all_factors = pd.merge_asof(
        df_monthly, df_fund, by='code', left_on='date', right_on='safe_date', direction='backward'
    )
    if 'safe_date' in df_all_factors.columns:
        df_all_factors = df_all_factors.drop(columns=['safe_date'])

    # 截面中位数填补上市初期缺失
    df_all_factors['roe'] = df_all_factors.groupby('date')['roe'].transform(lambda x: x.fillna(x.median()))
    df_all_factors['roe'] = df_all_factors['roe'].fillna(0.0)

    print(f" 大宽表构建完成！有效截面总行数: {len(df_all_factors)} 行。")
    return df_all_factors