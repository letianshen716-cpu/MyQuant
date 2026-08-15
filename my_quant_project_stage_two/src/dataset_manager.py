"""
Dataset Manager Module (结构化因子数据集管理引擎)
实现因子数据的统⼀格式存储、版本追溯与高效 IO 读写
"""

import pandas as pd
from pathlib import Path
import datetime

class DatasetManager:
    """数据集存储与版本控制模块"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_dataset(self, df: pd.DataFrame, dataset_name: str, use_versioning: bool = False) -> Path:
        """
        将因子大宽表保存为高性能 Parquet 格式
        :param dataset_name: 基础文件名 (如 'df_all_factors')
        :param use_versioning: 是否在文件名中追加时间戳版本号
        """
        if use_versioning:
            version_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{dataset_name}_v{version_str}.parquet"
        else:
            file_name = f"{dataset_name}.parquet"
            
        file_path = self.output_dir / file_name
        
        print(f"将数据序列化为 Parquet 格式: {file_path.name}")
        # 使用 pyarrow 引擎保存 parquet
        df.to_parquet(file_path, engine='pyarrow', index=False)
        print(f"数据形状: {df.shape}")
        
        return file_path

    def load_dataset(self, file_name: str) -> pd.DataFrame:
        """
        从存储目录加载 Parquet 数据集
        """
        file_path = self.output_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"找不到指定的数据集文件: {file_path}")
            
        print(f"加载数据集: {file_path.name}")
        df = pd.read_parquet(file_path, engine='pyarrow')
        print(f"数据形状: {df.shape}")
        return df