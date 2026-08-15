"""
Portfolio Vectorized Backtester Module (多因子投资组合向量化回测引擎)
"""

from typing import Dict, Literal, Optional, Tuple
import numpy as np
import pandas as pd


class PortfolioBacktester:
    """量化投资组合向量化回测引擎"""

    def __init__(
        self,
        top_n: Optional[int] = 50,
        top_quantile: Optional[float] = None,
        friction_cost: float = 0.003,
        weighting_method: Literal['equal', 'score_weighted'] = 'equal',
        annual_periods: int = 12,
        risk_free_rate: float = 0.02
    ):
        self.top_n = top_n
        self.top_quantile = top_quantile
        self.friction_cost = friction_cost
        self.weighting_method = weighting_method
        self.annual_periods = annual_periods
        self.rf = risk_free_rate

    def _select_portfolio_weights(self, group: pd.DataFrame, score_col: str) -> pd.DataFrame:
        df_sorted = group.dropna(subset=[score_col]).sort_values(by=score_col, ascending=False).copy()
        total_stocks = len(df_sorted)

        if total_stocks == 0:
            return pd.DataFrame()

        if self.top_n is not None:
            select_k = min(self.top_n, total_stocks)
        elif self.top_quantile is not None:
            select_k = max(1, int(total_stocks * self.top_quantile))
        else:
            select_k = min(50, total_stocks)

        selected_df = df_sorted.head(select_k).copy()

        if self.weighting_method == 'score_weighted':
            scores = selected_df[score_col] - selected_df[score_col].min() + 1e-4
            selected_df['weight'] = scores / scores.sum()
        else:
            selected_df['weight'] = 1.0 / select_k

        return selected_df

    @staticmethod
    def _calculate_turnover(
        prev_weights: Dict[str, float],
        curr_weights: Dict[str, float]
    ) -> float:
        all_codes = set(prev_weights.keys()).union(set(curr_weights.keys()))
        if not all_codes:
            return 0.0

        return 0.5 * sum(
            abs(curr_weights.get(code, 0.0) - prev_weights.get(code, 0.0))
            for code in all_codes
        )

    def run_backtest(
        self,
        df: pd.DataFrame,
        score_col: str = 'composite_score',
        ret_col: str = 'ret_next_month',
        benchmark_col: Optional[str] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, float]]:
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

            selected_df = self._select_portfolio_weights(group, score_col)
            if selected_df.empty:
                continue

            curr_weights_dict = dict(zip(selected_df['code'], selected_df['weight']))
            turnover = 1.0 if not prev_weights_dict else self._calculate_turnover(prev_weights_dict, curr_weights_dict)
            cost = turnover * (self.friction_cost * 2)

            gross_ret = (selected_df['weight'] * selected_df[ret_col]).sum()
            net_ret = gross_ret - cost

            bench_ret = group[benchmark_col].iloc[0] if (benchmark_col and benchmark_col in group.columns) else group[ret_col].mean()

            cum_nav *= (1.0 + net_ret)
            cum_benchmark_nav *= (1.0 + bench_ret)
            excess_ret = net_ret - bench_ret

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

            selected_df['date'] = d
            holdings_records.append(selected_df[['date', 'code', 'weight', score_col, ret_col]])
            prev_weights_dict = curr_weights_dict

        nav_df = pd.DataFrame(nav_records).set_index('date').sort_index()
        holdings_df = pd.concat(holdings_records, ignore_index=True) if holdings_records else pd.DataFrame()
        metrics_dict = self.calculate_performance_metrics(nav_df)

        return nav_df, holdings_df, metrics_dict

    def calculate_performance_metrics(self, nav_df: pd.DataFrame) -> Dict[str, float]:
        if nav_df.empty:
            return {}

        n_periods = len(nav_df)
        years = n_periods / self.annual_periods

        net_returns = nav_df['portfolio_net_return']
        excess_returns = nav_df['excess_return']
        nav_series = nav_df['portfolio_nav']

        total_return = nav_series.iloc[-1] - 1.0
        cagr = (nav_series.iloc[-1]) ** (1.0 / max(years, 1e-4)) - 1.0

        bench_nav = nav_df['benchmark_nav']
        bench_total_return = bench_nav.iloc[-1] - 1.0
        bench_cagr = (bench_nav.iloc[-1]) ** (1.0 / max(years, 1e-4)) - 1.0
        annualized_alpha = cagr - bench_cagr

        annualized_vol = net_returns.std() * np.sqrt(self.annual_periods)
        excess_vol = excess_returns.std() * np.sqrt(self.annual_periods)

        rolling_max = nav_series.cummax()
        drawdown_series = (nav_series - rolling_max) / rolling_max
        nav_df['drawdown'] = drawdown_series
        max_drawdown = abs(drawdown_series.min())

        downside_returns = net_returns[net_returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(self.annual_periods) if len(downside_returns) > 1 else 1e-6

        sharpe_ratio = (cagr - self.rf) / (annualized_vol + 1e-6)
        calmar_ratio = cagr / (max_drawdown + 1e-6)
        sortino_ratio = (cagr - self.rf) / (downside_vol + 1e-6)
        information_ratio = (excess_returns.mean() * self.annual_periods) / (excess_vol + 1e-6)

        win_rate = (net_returns > 0).mean()
        excess_win_rate = (excess_returns > 0).mean()
        avg_turnover = nav_df['turnover'].mean()

        pos_ret = net_returns[net_returns > 0].mean() if len(net_returns[net_returns > 0]) > 0 else 0.0
        neg_ret = abs(net_returns[net_returns < 0].mean()) if len(net_returns[net_returns < 0]) > 0 else 1e-6
        profit_loss_ratio = pos_ret / neg_ret

        return {
            'Total Return': round(float(total_return), 4),
            'Annualized Return (CAGR)': round(float(cagr), 4),
            'Benchmark Total Return': round(float(bench_total_return), 4),
            'Benchmark CAGR': round(float(bench_cagr), 4),
            'Annualized Alpha': round(float(annualized_alpha), 4),
            'Annualized Volatility': round(float(annualized_vol), 4),
            'Max Drawdown (MDD)': round(float(max_drawdown), 4),
            'Sharpe Ratio': round(float(sharpe_ratio), 4),
            'Calmar Ratio': round(float(calmar_ratio), 4),
            'Sortino Ratio': round(float(sortino_ratio), 4),
            'Information Ratio (IR)': round(float(information_ratio), 4),
            'Monthly Win Rate': round(float(win_rate), 4),
            'Excess Win Rate': round(float(excess_win_rate), 4),
            'Monthly Avg Turnover': round(float(avg_turnover), 4),
            'Profit-Loss Ratio': round(float(profit_loss_ratio), 4)
        }