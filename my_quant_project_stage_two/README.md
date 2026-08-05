# 因子挖掘与数据库引擎 (Factor Engine)

## 项目简介
本项目为多因子量化研究的底层引擎，包含从 MongoDB 拉取量价数据、横截面因子特征工程（行业缺失填充、MAD去极值、标准化、行业市值中性化）以及因子数据的自动化持久层入库。

## 目录结构
* `config.py`: 核心业务参数与全局路径配置。
* `utils/`: 因子处理工具箱 (`factor_tools.py`) 与因子数据库类 (`factor_db.py`)。
* `scripts/`: 批处理业务流水线执行脚本。
* `data/factor_db/`: Parquet 格式因子数据与 SQLite 元数据索引。

## 快速运行
1. 安装环境依赖：`pip install -r requirements.txt`
2. 确保本地 MongoDB 已启动并拥有底层日线数据。
3. 运行多因子全量批处理：`python scripts/01_run_multi_factor_batch.py`