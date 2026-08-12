# 阶段三：因子效果评估与 PIT 宽表构建引擎 (Factor Evaluation & PIT Assembly)

## 项目简介
本项目用于量化因子的回测评价与多维度特征拼接。核心功能包括：
1. 从底层数据库提取长周期全量数据并计算单因子（如20日动量）。
2. 在扣除交易摩擦成本（印花税、佣金、滑点）的前提下，进行日度/月度调仓的真实 Rank IC/IR 计算与 5 分组超额收益回测。
3. 引入安全发布日机制，利用 `merge_asof` 实现技术面与基本面财务数据的 PIT（Point-in-Time）防未来函数严格对齐。

## 目录结构
* `config.py`: 核心评估参数（摩擦成本、阈值）与全局路径配置。
* `utils/`: 包含批量检验引擎 (`factor_evaluator.py`) 与宽表拼接引擎 (`feature_builder.py`)。
* `scripts/`: 具体的业务执行流水线。
* `docs/`: 阶段性实验报告与因子有效性结论记录。
* `data/`: 存放历史因子库与高压缩比的 `.parquet` 大宽表。

## 快速运行
1. 安装环境依赖：`pip install -r requirements.txt`
2. 确保本地 MongoDB 实例运行正常。
3. 执行因子批量评价或宽表组装（进入 `scripts/` 目录运行对应脚本即可）。