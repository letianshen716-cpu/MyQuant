"""
Script 02: 全市场 PIT 多因子大宽表生成
执行批量前复权、技术面计算、行业映射与 PIT 财报严格对齐，生成 Parquet 大宽表
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
        return

    print(f"检测到 {len(all_codes)} 只标的股票")
    print(f" 批次大小: {BACKTEST_CONFIG.get('batch_size', 300)} 只")

    df_all_factors = build_pit_wide_table(all_codes)

    df_all_factors.to_parquet(WIDE_TABLE_PATH, index=False)
    print(f"\n全市场大宽表 {WIDE_TABLE_PATH}")
    print(f" {list(df_all_factors.columns)}")


if __name__ == '__main__':
    main()