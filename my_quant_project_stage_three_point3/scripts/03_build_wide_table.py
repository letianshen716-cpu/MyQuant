import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import ssl
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA
from utils.feature_builder import build_pit_wide_table
from config import WIDE_TABLE_PATH

def main():
    
    # 从本地数据库获取所有已有日线数据的去重股票代码
    all_codes = QA.DATABASE.stock_day.distinct('code')
    
    if not all_codes:
        return
        
    print(f"探测到 {len(all_codes)} 只股票。")
    
    # 将全市场代码传入构建引擎
    df_all_factors = build_pit_wide_table(all_codes)
    
    # 落地保存为高效的 Parquet 格式
    df_all_factors.to_parquet(WIDE_TABLE_PATH, index=False)
    print(f">>> 全市场大宽表已成功保存至: {WIDE_TABLE_PATH}")

if __name__ == '__main__':
    main()