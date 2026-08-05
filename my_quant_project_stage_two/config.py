from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"

# 因子数据库路径
FACTOR_DB_DIR = DATA_DIR / "factor_db"
FACTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

MONGO_URI = 'mongodb://localhost:27017/'

# 多因子计算测试股票池
FACTOR_STOCKS = ['000001', '000002', '600000', '600036', '600519', '000858', '002594']
FACTOR_START_DATE = '2022-01-01'
FACTOR_END_DATE = '2023-12-31'

# 因子去极值 MAD 乘数
MAD_MULTIPLIER = 3.0