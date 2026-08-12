"""
Portfolio Vectorized Backtester Module (多因子投资组合向量化回测引擎)
支持 Top N / 分位数选股、持仓权重计算、换手摩擦成本扣除及全维度绩效指标计算
"""

from typing import Dict, List, Literal, Optional, Tuple
import numpy as np
import pandas as pd


class PortfolioBacktester:
    """
    量化投资组合向量化回测引擎
    """

    def __init__(
        self,
        top_n: Optional[int] = 50,
        top_quantile: Optional[float] = None,
        friction_cost: float = 0.003,
        weighting_method: Literal['equal', 'score_weighted'] = 'equal',
        annual_periods: int = 12,
        risk_free_rate: float = 0.02
    ):
        """
        :param top_n: 每期选取的股票数量 (与 top_quantile 二选一，优先 top_n)
        :param top_quantile: 每期选取的头部比例 (如 0.1 表示选取前 10% 的股票)
        :param friction_cost: 单边交易摩擦成本 (印花税+佣金+滑点，如 0.003 表示 0.3%)
        :param weighting_method: 持仓权重分配方式 ('equal': 等权, 'score_weighted': 因子得分加权)
        :param annual_periods: 年化期数 (月度调仓填 12，周度填 52，日度填 252)
        :param risk_free_rate: 无风险年化利率 (默认 2%)
        """
        self.top_n = top_n
        self.top_quantile = top_quantile
        self.friction_cost = friction_cost
        self.weighting_method = weighting_method
        self.annual_periods = annual_periods
        self.rf = risk_free_rate

    def _select_portfolio_weights(self, group: pd.DataFrame, score_col: str) -> pd.DataFrame:
        """
        根据因子复合得分在单截面上确定选股名单与持仓权重
        """
        df_sorted = group.dropna(subset=[score_col]).sort_values(by=score_col, ascending=False).copy()
        total_stocks = len(df_sorted)

        if total_stocks == 0:
            return pd.DataFrame()

        # 确定当期入选股票数量
        if self.top_n is not None:
            select_k = min(self.top_n, total_stocks)
        elif self.top_quantile is not None:
            select_k = max(1, int(total_stocks * self.top_quantile))
        else:
            select_k = min(50, total_stocks)

        selected_df = df_sorted.head(select_k).copy()

        # 分配持仓权重
        if self.weighting_method == 'score_weighted':
            # 得分线性正定归一化
            scores = selected_df[score_col] - selected_df[score_col].min() + 1e-4
            selected_df['weight'] = scores / scores.sum()
        else:
            # 默认等权配置
            selected_df['weight'] = 1.0 / select_k

        return selected_df

    def _calculate_turnover(
        self,
        prev_weights: Dict[str, float],
        curr_weights: Dict[str, float]
    ) -> float:
        """
        计算调仓换手率: Turnover = 0.5 * \sum |w_{i, t} - w_{i, t-1}|
        """
        all_codes = set(prev_weights.keys()).union(set(curr_weights.keys()))
        if not all_codes:
            return 0.0

        turnover = 0.5 * sum(
            abs(curr_weights.get(code, 0.0) - prev_weights.get(code, 0.0))
            for code in all_codes
        )
        return turnover

    def run_backtest(
        self,
        df: pd.DataFrame,
        score_col: str = 'composite_score',
        ret_col: str = 'ret_next_month',
        benchmark_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
        """
        执行全流程向量化回测

        :param df: 输入大宽表 (需包含 date, code, score_col, ret_col)
        :param score_col: 因子复合得分列名
        :param ret_col: 目标持有期收益率列名
        :param benchmark_col: 基准收益率列名 (若为空，则以全市场截面等权收益为基准)
        :return: (nav_df, holdings_df, metrics_dict)
        """
        print(f">>> [回测引擎] 启动策略回测 (选股模式: Top {self.top_n if self.top_n else str(self.top_quantile*100)+'%'}, 费率: {self.friction_cost*100:.2f}%)...")

        dates = sorted(df['date'].unique())
        nav_records = []
        holdings_records = []

        prev_weights_dict: Dict[str, float] = {}
        cum_nav = 1.0
        cum_benchmark_nav = 1.0

        for d in dates:
            group = df[df['date'] == d].dropna(subset=[score_col, ret_col]).copy()
            if group.empty:
                continue

            # 1. 组合选股与权重构建
            selected_df = self._select_portfolio_weights(group, score_col)
            if selected_df.empty:
                continue

            curr_weights_dict = dict(zip(selected_df['code'], selected_df['weight']))

            # 2. 换手率与交易摩擦成本计算
            if not prev_weights_dict:
                # 初始建仓，换手率定义为 100%
                turnover = 1.0
            else:
                turnover = self._calculate_turnover(prev_weights_dict, curr_weights_dict)

            # 换手交易总成本: 买卖双边总额 = 2 * turnover，扣除费用
            cost = turnover * (self.friction_cost * 2)

            # 3. 投资组合收益率计算
            gross_ret = (selected_df['weight'] * selected_df[ret_col]).sum()
            net_ret = gross_ret - cost

            # 4. 基准收益率计算 (若未指定，默认采用当期全市场等权平均)
            if benchmark_col and benchmark_col in group.columns:
                bench_ret = group[benchmark_col].iloc[0]
            else:
                bench_ret = group[ret_col].mean()

            # 5. 累计净值更新
            cum_nav *= (1.0 + net_ret)
            cum_benchmark_nav *= (1.0 + bench_ret)
            excess_ret = net_ret - bench_ret

            # 6. 记录回测时序
            nav_records.append({
                'date': d,
                'portfolio_gross_return': gross_ret,
                'portfolio_net_return': net_ret,
                'benchmark_return': bench_ret,
                'excess_return': excess_ret,
                'turnover': turnover,
                'cost': cost,
                'portfolio_nav': cum_nav,
                'benchmark_nav': cum_benchmark_nav,
                'excess_nav': cum_nav / cum_benchmark_nav
            })

            # 记录持仓流水
            selected_df['date'] = d
            holdings_records.append(selected_df[['date', 'code', 'weight', score_col, ret_col]])

            prev_weights_dict = curr_weights_dict

        # 整理输出数据结构
        nav_df = pd.DataFrame(nav_records).set_index('date').sort_index()
        holdings_df = pd.concat(holdings_records, ignore_index=True) if holdings_records else pd.DataFrame()

        # 7. 计算全维度绩效指标
        metrics_dict = self.calculate_performance_metrics(nav_df)

        print(">>> [回测引擎] 回测完成！核心指标计算就绪。")
        return nav_df, holdings_df, metrics_dict

    def calculate_performance_metrics(self, nav_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算收益、风险、收益风险比与交易特征指标
        """
        if nav_df.empty:
            return {}

        n_periods = len(nav_df)
        years = n_periods / self.annual_periods

        net_returns = nav_df['portfolio_net_return']
        excess_returns = nav_df['excess_return']
        nav_series = nav_df['portfolio_nav']

        # 1. 收益指标
        total_return = nav_series.iloc[-1] - 1.0
        cagr = (nav_series.iloc[-1]) ** (1.0 / max(years, 1e-4)) - 1.0

        bench_nav = nav_df['benchmark_nav']
        bench_total_return = bench_nav.iloc[-1] - 1.0
        bench_cagr = (bench_nav.iloc[-1]) ** (1.0 / max(years, 1e-4)) - 1.0
        annualized_alpha = cagr - bench_cagr

        # 2. 风险指标
        annualized_vol = net_returns.std() * np.sqrt(self.annual_periods)
        excess_vol = excess_returns.std() * np.sqrt(self.annual_periods)

        # 最大回撤 (Max Drawdown)
        rolling_max = nav_series.cummax()
        drawdown_series = (nav_series - rolling_max) / rolling_max
        nav_df['drawdown'] = drawdown_series
        max_drawdown = abs(drawdown_series.min())

        # 下行标准差
        downside_returns = net_returns[net_returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(self.annual_periods) if len(downside_returns) > 1 else 1e-6

        # 3. 风险调整后收益
        sharpe_ratio = (cagr - self.rf) / (annualized_vol + 1e-6)
        calmar_ratio = cagr / (max_drawdown + 1e-6)
        sortino_ratio = (cagr - self.rf) / (downside_vol + 1e-6)
        information_ratio = (excess_returns.mean() * self.annual_periods) / (excess_vol + 1e-6)

        # 4. 胜率与交易特征
        win_rate = (net_returns > 0).mean()
        excess_win_rate = (excess_returns > 0).mean()
        avg_turnover = nav_df['turnover'].mean()

        pos_ret = net_returns[net_returns > 0].mean() if len(net_returns[net_returns > 0]) > 0 else 0.0
        neg_ret = abs(net_returns[net_returns < 0].mean()) if len(net_returns[net_returns < 0]) > 0 else 1e-6
        profit_loss_ratio = pos_ret / neg_ret

        return {
            'Total Return': round(total_return, 4),
            'Annualized Return (CAGR)': round(cagr, 4),
            'Benchmark Total Return': round(bench_total_return, 4),
            'Benchmark CAGR': round(bench_cagr, 4),
            'Annualized Alpha': round(annualized_alpha, 4),
            'Annualized Volatility': round(annualized_vol, 4),
            'Max Drawdown (MDD)': round(max_drawdown, 4),
            'Sharpe Ratio': round(sharpe_ratio, 4),
            'Calmar Ratio': round(calmar_ratio, 4),
            'Sortino Ratio': round(sortino_ratio, 4),
            'Information Ratio (IR)': round(information_ratio, 4),
            'Monthly Win Rate': round(win_rate, 4),
            'Excess Win Rate': round(excess_win_rate, 4),
            'Monthly Avg Turnover': round(avg_turnover, 4),
            'Profit-Loss Ratio': round(profit_loss_ratio, 4)
        }

    @staticmethod
    def get_metrics_table(metrics: Dict[str, float]) -> pd.DataFrame:
        """
        将指标字典转换为整洁的 DataFrame
        """
        df_metrics = pd.DataFrame(list(metrics.items()), columns=['Metric', 'Value'])
        return df_metrics