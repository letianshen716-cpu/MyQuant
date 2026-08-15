"""
Script 04: 打包生成可追溯的结构化因子宽表数据集
利用 DatasetManager 进行最终落盘，支持版本控制
"""

import sys
import pandas as pd
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import PROCESSED_DATA_DIR
from src import DatasetManager


def main():

    in_path = PROCESSED_DATA_DIR / "step3_neutralized_factors.parquet"
    if not in_path.exists():
        print(f"找不到上游数据 {in_path}，请先执行 03 脚本")
        return

    df_final = pd.read_parquet(in_path)
    
    # 剔除过程中产生的临时辅助列
    cols_to_drop = ['ln_size'] 
    df_final = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns])

    # 初始化数据集管理器
    manager = DatasetManager(output_dir=PROCESSED_DATA_DIR)

    # 1. 覆盖保存通用大宽表 
    manager.save_dataset(df_final, dataset_name="df_all_factors", use_versioning=False)
    
    # 2. 生成带时间戳版本号的快照备份
    manager.save_dataset(df_final, dataset_name="df_all_factors", use_versioning=True)

if __name__ == "__main__":
    main()