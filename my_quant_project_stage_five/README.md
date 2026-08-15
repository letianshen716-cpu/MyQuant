# MyQuant 多因子量化投研系统

## 1. 项目简介 (已推进至第五阶段：策略绩效归因与量化研究结论整合)
MyQuant 是一套面向 A 股市场的多阶段多因子量化实证与策略研发系统。目前项目已完整跑通全生命周期，并成功交付**第五阶段**的核心任务。系统不仅涵盖底层数据提取、PIT (Point-in-Time) 截面对齐、单因子检验、对称正交化降维与组合回测，更在最终阶段实现了深度的收益归因（Alpha/Beta 拆解）、全面风险评估以及机构级可视化看板与研究总报告的输出。

## 2. 第五阶段核心产出说明
本阶段圆满完成了量化闭环的最终交付，核心产出存放于 `docs/reports/` 目录下：
* **产出 1：策略绩效归因与风险评估看板** (`05_strategy_risk_dashboard.png` 等)
  * **收益归因**：基于 CAPM 模型精准拆解 Alpha 纯净收益与风格/市场 Beta 贡献，定位核心盈利驱动因子。
  * **风险评估**：全面分析最大回撤 (MDD)、下行风险、尾部暴露特征，并测算牛熊市上下行捕获率 (Capture Ratios)。
* **产出 2：完整量化研究总报告** (`05_final_research_report.md`)
  * 总结全流程量化研究发现，覆盖研究背景、数据清洗工艺、特征工程方法。
  * 提炼因子有效性规律（如缩量溢价、短期反转特征）与策略适用边界（如“等权之谜”优势）。
  * 结合市场环境剖析策略局限性（如高换手率损耗），并提出后续研究优化方向。
* **产出 3：项目成果演示材料** (`06_presentation_deck.md`)
  * 专为部门内部研究成果汇报与业务场景分享设计的结构化演示大纲，直击核心结论与业务落地价值。

## 3. 核心架构与目录结构
```text
my_quant/
├── README.md                               # 项目总览（第五阶段最终版）
├── requirements.txt                        # 项目核心依赖库与版本清单
├── .gitignore                              # Git 忽略配置
│
├── config/                                 # 【独立配置层】
│   ├── __init__.py
│   └── settings.py                         # 动态相对路径、数据库连接与量化超参数
│
├── data/                                   # 【数据存储层】
│   ├── raw_data/                           # 原始行情与财报落地缓存
│   └── processed_data/                     # 清洗后的特征大宽表与回测落盘结果
│
├── docs/                                   # 【文档与报告层】(第五阶段交付核心)
│   └── reports/                            
│       ├── 01_data_extraction_report.md    
│       ├── 02_feature_engineering_report.md
│       ├── 03_single_factor_report.md      
│       ├── 04_multi_factor_backtest.md     
│       ├── 05_final_research_report.md     # [第五阶段] 完整量化研究总报告
│       ├── 05_strategy_risk_dashboard.png  # [第五阶段] 风险评估与可视化热力图看板
│       └── 06_presentation_deck.md         # [第五阶段] 成果汇报演示材料
│
├── src/                                    # 【核心算法层】
│   ├── ...                                 # 因子评估、合成、回测等底层引擎
│   ├── performance_attributor.py           # [第五阶段] CAPM 归因、行业收益拆解与捕获率计算引擎
│   └── portfolio_backtester.py             
│
└── scripts/                                # 【自动化流水线层】
    ├── 00_download_data.py                 
    ├── 01_generate_history_factor.py       
    ├── 02_build_wide_table.py              
    ├── 03_evaluate_single_factor.py        
    ├── 04_run_strategy_backtest.py         
    └── 05_generate_risk_dashboard.py       # [第五阶段] 执行收益归因拆解与风险看板生成
```


## 环境配置与启动指南
### 第一步：安装依赖
```bash
pip install -r requirements.txt
```

### 第二步：按序执行全生命周期流水线
为了复现第五阶段的最终报告与图表，请依次执行以下脚本：
```bash
# 0. 下载基础板块与财务数据
python scripts/00_download_data.py

# 1. 抽取历史底层量价因子
python scripts/01_generate_history_factor.py

# 2. 构建全市场 PIT 多因子大宽表
python scripts/02_build_wide_table.py

# 3. 单因子批量检验、特征筛选与异质性分析
python scripts/03_evaluate_single_factor.py

# 4. 多方案因子加权与选股策略全样本回测
python scripts/04_run_strategy_backtest.py

# 5. [第五阶段核心] 策略收益归因分析与可视化风险看板生成
python scripts/05_generate_risk_dashboard.py
```