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

    # 1. 从数据库读取全量股票代码
    all_codes = QA.DATABASE.stock_day.distinct('code')

    if not all_codes:
        return

    print(f">>> 共检测到 {len(all_codes)} 只标的股票。")
    print(f">>> 启动分批构建引擎 (批次大小: {BACKTEST_CONFIG.get('batch_size', 300)} 只)")

    # 2. 调用核心构建模块 (分批复权 + 行业匹配 + PIT 财报对齐)
    df_all_factors = build_pit_wide_table(all_codes)

    # 3. 落盘为高性能 Parquet 格式
    df_all_factors.to_parquet(WIDE_TABLE_PATH, index=False)
    print(f"\n全市场大宽表已成功落盘至: {WIDE_TABLE_PATH}")
    print(f">>> 包含字段: {list(df_all_factors.columns)}")


if __name__ == '__main__':
    main()