# MyQuant 多因子量化投研系统

## 1. 项目简介
MyQuant 是一套面向 A 股市场的多阶段多因子量化实证与策略研发系统。系统涵盖底层数据抽取、PIT (Point-in-Time) 截面对齐、单因子 Alpha 检验、对称正交化降维、统计学习特征筛选及多因子组合回测全流程。

## 2. 目录结构说明
* **`config/`**：集中管理项目根路径动态解析、MongoDB 数据库配置、因子计算参数与回测交易费率。
* **`data/`**：数据存储层，包含原始行情与清洗后的特征大宽表（`data/processed/df_all_factors.parquet`）。
* **`docs/reports/`**：记录各研发阶段的实验设计、参数设定、核心指标输出与归因分析报告。
* **`src/`**：核心计算引擎层（包含 MAD 去极值、Z-score、Rank IC 计算、对称正交化、Lasso 特征选择、因子动态合成及向量化回测引擎）。
* **`scripts/`**：按数字顺序编号的自动化流水线执行脚本。

## 3. 快速启动流水线

### 第一步：环境配置
```bash
pip install -r requirements.txt
```

### 第二步：按序执行流水线脚本
```bash
# 0. 下载全市场股票板块分类及财务基础数据
python scripts/00_download_data.py

# 1. 抽取底层量价历史因子并落盘
python scripts/01_generate_history_factor.py[cite: 1]

# 2. 构建全市场 PIT 多维因子大宽表 (支持分批加载与内存回收)
python scripts/02_build_wide_table.py[cite: 3, 5, 6]

# 3. 运行单因子批量显著性检验、对称正交化及异质性分析
python scripts/03_evaluate_single_factor.py

# 4. 执行多因子组合策略回测与稳健性测试
python scripts/04_run_strategy_backtest.py
```