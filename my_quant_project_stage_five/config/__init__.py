"""
Configuration Package Initialization
集中暴露全局动态路径与系统超参数
"""

from config.settings import (
    BACKTEST_CONFIG,
    DATA_DIR,
    DB_NAME,
    FACTOR_ALL_HISTORY_PATH,
    FACTOR_CONFIG,
    MONGO_URI,
    PROCESSED_DATA_DIR,
    PROJECT_ROOT,
    RAW_DATA_DIR,
    REPORTS_DIR,
    WIDE_TABLE_PATH,
)

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "REPORTS_DIR",
    "WIDE_TABLE_PATH",
    "FACTOR_ALL_HISTORY_PATH",
    "MONGO_URI",
    "DB_NAME",
    "BACKTEST_CONFIG",
    "FACTOR_CONFIG",
]