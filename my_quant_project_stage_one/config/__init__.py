"""
Configuration Package Initialization
集中暴露全局动态路径与第一阶段研究基线参数
"""

from .settings import (
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    REPORTS_DIR,
    MONGO_URI,
    START_YEAR,
    END_YEAR,
    TARGET_SYMBOLS
)

__all__ = [
    "PROJECT_ROOT",
    "DATA_DIR",
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "REPORTS_DIR",
    "MONGO_URI",
    "START_YEAR",
    "END_YEAR",
    "TARGET_SYMBOLS"
]