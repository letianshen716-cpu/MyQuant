# MyQuant - 第三阶段：单因子有效性实证检验与因子正交化研究

## 1. 项目简介
本项目目前聚焦于量化投研的第三阶段：核心目标是**单因子有效性实证检验与因子正交化研究**。
本阶段基于前置构建的 PIT 防未来函数多因子大宽表，采用 IC/IR、分层回测等行业标准方法，对因子 Alpha 能力进行全方位的统计显著性验证。同时，引入**对称正交化（Symmetric Orthogonalization）**以消除多因子间的线性共线性干扰，并结合 **LassoCV 惩罚回归**进行核心特征筛选。最后，框架支持多维度的因子异质性分析（如牛熊市状态、不同行业板块），清晰界定因子的适用场景与阶段性失效规律，为后续构建稳健的多因子复合模型奠定核心基础。

## 2. 核心架构与目录
* **`config/`**：独立配置层，集中管理 MongoDB 数据库 URI、文件路径及单边摩擦成本（如 0.3%）等预处理超参数。
* **`data/`**：数据存储层，包含清洗生成的历史因子 CSV 序列及最终对齐的高效列式存储大宽表 (`df_all_factors_2.parquet`)。
* **`docs/reports/`**：核心实证报告存放处，用于归档《单因子有效性实证研究报告》（包含相关性矩阵、正交化对比、因子异质性归因等）。
* **`utils/`**：核心算法工具箱，高度封装了 `BatchFactorEvaluator` (批量评估引擎)、`FactorOrthogonalizer` (正交化处理)、`StatisticalSelector` (统计学习筛选) 与 `HeterogeneityAnalyzer` (异质性分析)。
* **`scripts/`**：执行脚本层，实现从底座数据组装到自动化因子检验的流水线。

## 3. 环境配置与启动指南

**环境要求**：建议使用 Python 3.8 及以上版本。

**第一步：获取代码与安装依赖**
```bash
git clone <你的远程仓库地址>
cd <项目目录>
pip install -r requirements.txt
```

**第二步：本地数据与环境准备**
在运行流水线前，请确保本地 MongoDB 数据库已启动，且通过 QUANTAXIS 框架完成 stock_day 量价数据、财务数据集以及 stock_block 板块分类数据的全量本地同步。

**第三步：按序执行流水线**

```bash
# 1. 数据底座提取：抽取全市场底层量价数据并生成基础历史因子 (如 10日/20日反转)
python scripts/01_generate_history_factor_3.py

# 2. 宽表构建：融合量价特征与财务数据，执行 PIT 严格时序对齐，落地 Parquet 大宽表
python scripts/03_build_wide_table_3.py

# 3. 因子验证：读取大宽表，执行横截面去极值/标准化、Lasso 筛选、显著性检验及异质性分析
python scripts/02_evaluate_single_factor_3.py

# 4. 正交化与相关性深度分析：计算截面相关性矩阵，输出对称正交化前后的 Alpha 效能对比
python scripts/04_supplementary_orth_analysis.py
```