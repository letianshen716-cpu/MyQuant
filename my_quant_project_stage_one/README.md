# MyQuant 因子挖掘与量化分析项目

## 项目简介
本项目用于 A 股市场的历史数据获取、因子预处理（去极值、标准化、中性化）以及量化策略的回测实验。

## 目录结构
* `config.py`：项目的全局参数与相对路径管理。
* `scripts/`：存放数据下载、清洗与质检的核心执行脚本。
* `docs/`：存放每个重要开发节点的实验报告与结论记录。
* `data/`：本地数据集输出目录。

## 快速开始
1. 安装依赖：`pip install -r requirements.txt`
2. 运行数据质检脚本验证数据库连接：`python scripts/02_check_data_status.py`