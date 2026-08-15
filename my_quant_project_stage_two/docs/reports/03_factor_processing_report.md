# 节点 3：MAD去极值、Z-score标准化与行业/市值中性化分布检验

## 1. 特征工程的数学目标
经过清洗的原始因子（Raw Factors）往往存在量纲不一、极端偏态、以及严重的行业与大小盘风格暴露问题。本节点的任务是将原始特征转化为正态分布、互相可比且风格中性的纯净信号（Pure Alpha）。

## 2. 去极值与标准化处理
### 2.1 截面 MAD 去极值 (Winsorization)
相比于均值-标准差去极值，绝对中位差 (Median Absolute Deviation) 对异常点具备更强的鲁棒性。
1.  计算横截面因子的中位数 $X_{median}$。
2.  计算每个样本偏离中位数的绝对值的中位数 $MAD$：
    $$MAD = Median(|X_i - X_{median}|)$$
3.  将因子值限制在 $3.0 \times MAD$ 的区间内：
    $$X_{clip} = \min(\max(X, X_{median} - 3.0148 \times MAD), X_{median} + 3.0148 \times MAD)$$

### 2.2 Z-score 标准化
将去极值后的数据转化为均值为 0，标准差为 1 的标准正态分布，消除量纲差异，使得动量因子与 ROE 因子可以直接相加：
$$Z = \frac{X_{clip} - \mu}{\sigma}$$

## 3. OLS 行业与市值中性化 (Neutralization)
因子往往自带“大盘属性”或“特定行业属性”（如银行股常年低 PE）。为了萃取真正的选股 Alpha，需要通过多元线性回归剥离这些系统性风险（Beta）。

在每日横截面上，将标准化后的因子 $F_i$ 作为因变量，个股市值的自然对数 $\ln(Size)$ 与所属行业的虚拟变量（Dummy Variables）作为自变量进行 OLS 回归：
$$F_i = \beta_0 + \beta_1 \ln(Size_i) + \sum_{j=1}^{K} \beta_j Industry_{i,j} + \epsilon_i$$

**结论与输出**：回归方程的**残差项 $\epsilon_i$** 就是剥离了市值规模和行业影响后的“纯正因子值 (Neutralized Factor)”。以此建立的结构化数据集，为后续多因子模型的线性加权与组合优化消除了极大的多重共线性隐患。