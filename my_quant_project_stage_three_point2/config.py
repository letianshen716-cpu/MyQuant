from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 历史因子保存路径
FACTOR_ALL_HISTORY_PATH = PROCESSED_DIR / "df_factor_all_history.csv"
WIDE_TABLE_PATH = PROCESSED_DIR / "df_all_factors.parquet"

MONGO_URI = 'mongodb://localhost:27017/'

# 交易摩擦成本 (印花税+佣金+滑点)
DAILY_FRICTION_COST = 0.001   # 日度调仓成本 (0.1%)
MONTHLY_FRICTION_COST = 0.003 # 月度调仓成本 (0.3%)
MIN_STOCKS_PER_CROSS_SECTION = 30 # 截面有效股票数下限