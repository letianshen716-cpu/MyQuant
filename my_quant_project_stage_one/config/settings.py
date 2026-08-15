"""
Global Configuration & Parameter Settings Module
集中管理全局动态相对路径、数据库连接与第一阶段研究基线参数
"""

from pathlib import Path

# ================= 1. 动态相对路径解析 =================
# 解析项目根目录 (自动向上跳转一级找到 my_quant 根目录)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 核心数据与文档目录层级
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw_data"
PROCESSED_DATA_DIR = DATA_DIR / "processed_data"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = DOCS_DIR / "reports"

# ================= 2. 数据库配置 =================
# MongoDB 连接 URI (用于后续 QUANTAXIS 或自定义数据源接入)
MONGO_URI = "mongodb://localhost:27017"

# ================= 3. 研究样本基线参数 =================
# 设定全样本回溯的时间窗口 (2020-2026)
START_YEAR = 2020
END_YEAR = 2026

# 第一阶段用于流水线测试的基础标的池 (后续阶段将替换为全市场 A 股代码)
TARGET_SYMBOLS = ["000001", "600000"]