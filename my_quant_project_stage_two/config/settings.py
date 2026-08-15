"""
Global Configuration & Parameter Settings Module
集中管理全局动态相对路径与量化预处理超参数
"""

import ssl
from pathlib import Path

# ================= 0. 全局 SSL 证书补丁 =================
# 防止在某些网络环境下请求外部数据源时报 SSL 证书错误
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

# ================= 2. 因子计算与预处理超参数 =================
FACTOR_CONFIG = {
    "mad_multiplier": 3.0,          # MAD 去极值中位差倍数 (通常设置为 3.0 或 5.0)
    "momentum_short_window": 10,    # 短期反转周期 (10日)
    "momentum_mid_window": 20,      # 中期反转周期 (20日)
    "volatility_window": 20,        # 波动率滚动计算周期 (20日)
    "amount_mean_window": 20,       # 平均成交额/成交量滚动计算周期 (20日)
}