import os
import sqlite3
import pandas as pd
import datetime

# 动态导入全局路径
from config import FACTOR_DB_DIR

class FactorDatabase:
    """
    结构化因子数据库
    实现因子数据的统一存储、版本控制与快速调用
    """
    def __init__(self, base_dir=FACTOR_DB_DIR):
        self.base_dir = str(base_dir)
        self.data_dir = os.path.join(self.base_dir, "data")
        self.meta_db_path = os.path.join(self.base_dir, "metadata.sqlite")
        
        os.makedirs(self.data_dir, exist_ok=True)
        self._init_metadata_db()

    def _init_metadata_db(self):
        """初始化 SQLite 元数据库，用于版本溯源"""
        conn = sqlite3.connect(self.meta_db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS factor_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factor_name TEXT NOT NULL,
                version TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_path TEXT NOT NULL,
                UNIQUE(factor_name, version)
            )
        ''')
        conn.commit()
        conn.close()

    def save_factor(self, df: pd.DataFrame, factor_name: str, version: str, description: str = ""):
        """
        保存因子数据并记录版本
        df 必须包含 ['date', 'ticker', 'value'] 列
        """
        if not {'date', 'ticker', 'value'}.issubset(df.columns):
            raise ValueError("DataFrame 必须包含 'date', 'ticker', 'value' 基础列。")

        # 确保 date 列格式为字符串
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 存储路径按 因子名/版本 隔离
        factor_path = os.path.join(self.data_dir, factor_name, version)

        # 使用 PyArrow 保存为按天分区的 Parquet
        df.to_parquet(
            factor_path,
            engine='pyarrow',
            partition_cols=['date'],
            index=False,
            existing_data_behavior='overwrite_or_ignore' 
        )

        # 注册或更新元数据
        conn = sqlite3.connect(self.meta_db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO factor_metadata (factor_name, version, description, data_path)
                VALUES (?, ?, ?, ?)
            ''', (factor_name, version, description, factor_path))
        except sqlite3.IntegrityError:
            cursor.execute('''
                UPDATE factor_metadata 
                SET description = ?, data_path = ?, created_at = CURRENT_TIMESTAMP
                WHERE factor_name = ? AND version = ?
            ''', (description, factor_path, factor_name, version))
        conn.commit()
        conn.close()
        print(f"因子 [{factor_name} | {version}] 已持久化存储。")

    def load_factor(self, factor_name: str, version: str = "latest", start_date: str = None, end_date: str = None, tickers: list = None) -> pd.DataFrame:
        """
        快速调用因子数据，支持按日期和标的进行底层过滤
        """
        conn = sqlite3.connect(self.meta_db_path)
        if version == "latest":
            query = "SELECT version, data_path FROM factor_metadata WHERE factor_name = ? ORDER BY created_at DESC LIMIT 1"
            result = conn.execute(query, (factor_name,)).fetchone()
        else:
            query = "SELECT version, data_path FROM factor_metadata WHERE factor_name = ? AND version = ?"
            result = conn.execute(query, (factor_name, version)).fetchone()
        conn.close()

        if not result:
            raise FileNotFoundError(f"未找到因子: {factor_name} (版本: {version})")

        target_version, data_path = result
        print(f"正在加载 [{factor_name}] 版本: {target_version} ")

        # 构造 PyArrow 过滤器 
        filters = []
        if start_date:
            filters.append(('date', '>=', start_date))
        if end_date:
            filters.append(('date', '<=', end_date))
        if tickers:
            filters.append(('ticker', 'in', tickers))

        # 读取时只加载符合条件的数据块
        df = pd.read_parquet(
            data_path, 
            engine='pyarrow', 
            filters=filters if filters else None
        )
        return df

    def list_factors(self) -> pd.DataFrame:
        """展示系统内所有因子及其版本信息"""
        conn = sqlite3.connect(self.meta_db_path)
        df = pd.read_sql("SELECT factor_name, version, description, created_at FROM factor_metadata ORDER BY factor_name, created_at DESC", conn)
        conn.close()
        return df