"""
Script 02: 全市场 PIT 多因子大宽表生成
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import BACKTEST_CONFIG, WIDE_TABLE_PATH
from src.feature_builder import build_pit_wide_table
import QUANTAXIS as QA

def main():

    all_codes = QA.DATABASE.stock_day.distinct('code')
    if not all_codes:
        print("本地数据库无行情数据。")
        return

    print(f"检测到 {len(all_codes)} 只标的股票。正在分批构建大宽表")
    df_all_factors = build_pit_wide_table(all_codes)
    
    df_all_factors.to_parquet(WIDE_TABLE_PATH, index=False)
    print(f"\n全市场大宽表已成功落盘至: {WIDE_TABLE_PATH}")

if __name__ == '__main__':
    main()