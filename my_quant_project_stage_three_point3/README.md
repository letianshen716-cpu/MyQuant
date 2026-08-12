# MyQuant 多因子量化投研系统

## 1. 项目简介
本项目面向 A 股市场，涵盖数据清洗、PIT 截面对齐、单因子 Alpha 检验、对称正交化、统计学习特征筛选及多因子组合回测全流程。

## 2. 目录结构说明
* `config/`：全局参数配置与路径管理。
* `data/`：行情原始数据（raw）与清洗后的大宽表（processed）。
* `docs/reports/`：各研发阶段的过程记录与实证结论报告。
* `scripts/`：按数字顺序编号的自动化流水线执行脚本。
* `utils/`：核心算法引擎（MAD去极值、标准化、正交化、异质性分析）。

## 3. 运行指南
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 构建大宽表
python scripts/03_build_wide_table.py

# 3. 执行单因子评估与正交化检验
python scripts/02_evaluate_single_factor.py