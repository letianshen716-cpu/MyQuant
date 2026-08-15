# 第二阶段：多维度因子体系构建与量化预处理研究

## 1. 项目简介
本项目目前聚焦于量化投研的第二阶段：核心目标是构建多维度因子体系并完成高标准的量化预处理研究。本阶段打通了基本面、技术面等核心因子的底层计算逻辑，并针对金融数据典型的缺失值、前视偏差（Look-ahead Bias）设计了 PIT (Point-in-Time) 严格时序对齐与清洗方案。最终通过横截面 MAD 去极值、Z-score 标准化及 OLS 行业与市值中性化，输出了纯净且高质量的结构化因子宽表数据集。

## 2. 核心架构与目录
* **`config/`**：独立配置层，集中管理动态相对路径与因子预处理超参数。
* **`data/`**：数据存储层，包含原始缓存 (`raw_data/`) 与清洗落盘特征 (`processed_data/`)。
* **`docs/reports/`**：核心实证报告存放处，用于记录因子设计、清洗规则与去极值分布检验结果。
* **`src/`**：核心算法层，封装因子计算、数据清洗、中性化处理与数据集落地引擎。
* **`scripts/`**：执行脚本层，按数字序号编排的自动化流水线。

## 3. 环境配置与启动指南

**第一步：安装依赖**
```bash
pip install -r requirements.txt
```

**第二步：按序执行**
```bash
# 1. 底层全量基础因子计算 (包含 20+ 技术/基本/另类因子)
python scripts/01_calculate_raw_factors.py

# 2. 金融数据清洗与 PIT 时序严格对齐
python scripts/02_execute_data_cleaning.py

# 3. 因子特征去极值、标准化与中性化处理
python scripts/03_run_factor_neutralization.py

# 4. 打包生成可追溯的结构化因子宽表数据集
python scripts/04_build_structured_dataset.py

# 5. 自动扫描数据质量并生成 Markdown 实证报告
python scripts/05_generate_quality_report.py
```