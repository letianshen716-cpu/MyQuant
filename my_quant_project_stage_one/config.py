# config.py
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

DATA_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)

TEST_STOCKS = ['000001', '600519']
CHECK_START_DATE = '2021-12-25'
CHECK_END_DATE = '2026-07-28'