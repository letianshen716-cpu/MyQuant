import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import ssl
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

from utils.feature_builder import build_pit_wide_table
from config import WIDE_TABLE_PATH

def main():
    df_all_factors = build_pit_wide_table() 
    df_all_factors.to_parquet(WIDE_TABLE_PATH, index=False) 
    print(f"大宽表已保存至: {WIDE_TABLE_PATH}")

if __name__ == '__main__':
    main()