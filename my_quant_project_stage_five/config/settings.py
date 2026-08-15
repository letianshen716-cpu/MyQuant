"""
Global Configuration & Parameter Settings Module
集中管理全局动态相对路径、数据库连接、因子超参数与回测交易规则
"""

import ssl
from pathlib import Path

# ================= 0. 全局 SSL 证书补丁 =================
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()


# ================= 1. 动态相对路径解析 =================
# 解析项目根目录 (自动向上跳转一级找到 my_quant 根目录)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 核心数据与文档目录层级
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw_data"
PROCESSED_DATA_DIR = DATA_DIR / "processed_data"
DOCS_DIR = PROJECT_ROOT / "docs"
REPORTS_DIR = DOCS_DIR / "reports"

# 自动确保底层所需的所有目录树存在
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 核心数据落地文件路径
WIDE_TABLE_PATH = PROCESSED_DATA_DIR / "df_all_factors.parquet"
FACTOR_ALL_HISTORY_PATH = PROCESSED_DATA_DIR / "factor_all_history.csv"


# ================= 2. 数据库配置 =================
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "quantaxis"


# ================= 3. 回测与量化模型参数 =================
BACKTEST_CONFIG = {
    "start_date": "2020-01-01",
    "end_date": "2026-12-31",
    "friction_cost": 0.003,         # 单边调仓摩擦成本 (含印花税、佣金与滑点 0.3%)
    "min_stocks_per_cross": 30,     # 单一截面有效计算的最小样本股票数
    "quantiles": 5,                 # 分层回测分组数
    "hold_top_n": 50,               # 多头组合固定持仓标的数量
    "batch_size": 500,              # 数据库分批读取批次大小 (防 OOM)
    "annual_periods": 12,           # 月度调仓年化期数
    "risk_free_rate": 0.02          # 无风险年化利率 (2.0%)
}


# ================= 4. 因子计算超参数 =================
FACTOR_CONFIG = {
    "momentum_short_window": 10,    # 短期反转周期 (如: 10日)
    "momentum_mid_window": 20,      # 中期反转周期
    "volatility_window": 20,        # 波动率滚动计算周期
    "amount_mean_window": 20,       # 平均成交额滚动计算周期
    "mad_multiplier": 3.0           # MAD 去极值中位差倍数
}