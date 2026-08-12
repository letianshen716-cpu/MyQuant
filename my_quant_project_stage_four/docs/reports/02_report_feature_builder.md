# 阶段二：PIT 大宽表构建与特征工程报告

## 1. 实验目标
* **核心目标**：融合全市场前复权量价特征与定期财务报表数据，构建月度截面多因子大宽表。
* **防未来函数**：严格执行 PIT (Point-in-Time) 无偏对齐，确保所有特征在截面时点绝对可见。

## 2. 核心处理工艺
### 2.1 分批前复权与技术因子降频
* **分批加载 (Chunking)**：针对行情数据，采用 300 只股票/批次；针对财务数据，采用 500 只股票/批次的智能探针提取法，彻底解决了 MongoDB 传输限制与 `MemoryError` 内存溢出问题。
* **量价特征构建**：包含 `momentum_10d`、`momentum_20d`、`volatility` (20日滚动波动率) 以及 `amt_mean_20d` (20日平均成交额)。数据统一降频至每个自然月的最后一个交易日。

### 2.2 PIT (Point-in-Time) 财报严格对齐
为杜绝财报数据的“前瞻偏差”，根据 A 股法定披露规则构建安全可用日期 (`safe_date`)：
* 一季报（3月31日）：安全可用日 `5月1日`
* 中报（6月30日）：安全可用日 `9月1日`
* 三季报（9月30日）：安全可用日 `11月1日`
* 年报（12月31日）：安全可用日次年 `5月1日`
* **对齐方式**：使用 `pandas.merge_asof(direction='backward')` 将月度截面与最新的安全财务记录向后拼合。

### 2.3 行业映射降级策略
自适应探测 `stock_block` 集合，将 A 股分类为：`Finance/LargeCap` (大金融)、`Growth/Tech` (科技成长)、`Manufacturing` (制造) 与 `Others`。当数据库缺失映射时，智能降级为基于股票代码前缀（如 601、688）的规则匹配。

## 3. 实验产出
* **宽表输出**：`data/processed/df_all_factors.parquet` (列式存储极大提升了下游加载速度)。
* **包含字段**：date, code, industry, momentum_10d, momentum_20d, volatility, amt_mean_20d, roe, market_state, ret_next_month。