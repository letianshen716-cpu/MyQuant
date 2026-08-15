"""
Performance Attributor Module (策略绩效归因与收益拆解引擎)
支持基于 CAPM 模型拆解 Alpha/Beta、计算牛熊上下行捕获率及行业收益贡献
"""

from typing import Dict
import numpy as np
import pandas as pd
import statsmodels.api as sm


class PerformanceAttributor:
    """策略收益与风险归因分析引擎"""

    def __init__(self, risk_free_rate: float = 0.02, annual_periods: int = 12):
        """
        :param risk_free_rate: 无风险年化利率 (默认 2%)
        :param annual_periods: 年化期数 (月度数据填 12)
        """
        self.rf = risk_free_rate
        self.annual_periods = annual_periods
        self.rf_period = (1 + self.rf) ** (1 / self.annual_periods) - 1.0

    def regress_alpha_beta(self, nav_df: pd.DataFrame) -> Dict[str, float]:
        """
        基于 OLS 时间序列回归 (CAPM 模型) 拆解 Alpha 与 Beta
        R_portfolio - R_f = Alpha + Beta * (R_benchmark - R_f) + epsilon
        """
        if nav_df.empty or 'portfolio_net_return' not in nav_df.columns or 'benchmark_return' not in nav_df.columns:
            return {}

        y = nav_df['portfolio_net_return'] - self.rf_period
        x = nav_df['benchmark_return'] - self.rf_period
        X = sm.add_constant(x)

        try:
            model = sm.OLS(y, X).fit()
            alpha_period = model.params.iloc[0]
            beta = model.params.iloc[1]
            
            annualized_alpha = alpha_period * self.annual_periods
            r_squared = model.rsquared
            p_value_alpha = model.pvalues.iloc[0]
            
            return {
                'Market Beta (系统性风险敞口)': round(float(beta), 4),
                'Jensen\'s Alpha (纯净年化超额)': round(float(annualized_alpha), 4),
                'R-Squared (基准解释度)': round(float(r_squared), 4),
                'Alpha P-Value (Alpha显著性)': round(float(p_value_alpha), 4)
            }
        except Exception as e:
            print(f"Alpha-Beta 回归分析失败: {e}")
            return {}

    def calculate_capture_ratios(self, nav_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算上行捕获率 (Up-Market Capture) 与 下行捕获率 (Down-Market Capture)
        """
        if nav_df.empty:
            return {}

        port_ret = nav_df['portfolio_net_return']
        bench_ret = nav_df['benchmark_return']

        up_mask = bench_ret > 0
        down_mask = bench_ret <= 0

        def geom_mean(returns):
            if len(returns) == 0:
                return 0.0
            return np.prod(1 + returns) ** (1 / len(returns)) - 1.0

        up_port = geom_mean(port_ret[up_mask])
        up_bench = geom_mean(bench_ret[up_mask])
        
        down_port = geom_mean(port_ret[down_mask])
        down_bench = geom_mean(bench_ret[down_mask])

        up_capture = (up_port / up_bench) if up_bench > 0 else 0.0
        down_capture = (down_port / down_bench) if down_bench < 0 else 0.0
        capture_spread = up_capture - down_capture

        return {
            'Up-Market Capture Ratio (上行捕获率)': round(float(up_capture), 4),
            'Down-Market Capture Ratio (下行捕获率)': round(float(down_capture), 4),
            'Capture Ratio Spread (捕获利差)': round(float(capture_spread), 4)
        }

    def attribute_holdings_by_industry(self, holdings_df: pd.DataFrame, wide_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算行业维度的收益贡献与配置权重占比
        """
        if holdings_df.empty or wide_df.empty:
            return pd.DataFrame()

        merged_df = pd.merge(holdings_df, wide_df[['date', 'code', 'industry']], on=['date', 'code'], how='left')
        
        if 'industry' not in merged_df.columns:
            return pd.DataFrame()

        merged_df['contribution'] = merged_df['weight'] * merged_df['ret_next_month']

        industry_stats = merged_df.groupby('industry').agg(
            Total_Contribution=('contribution', 'sum'),
            Average_Weight=('weight', 'mean')
        ).reset_index()
        
        total_ret = industry_stats['Total_Contribution'].sum()
        if total_ret != 0:
            industry_stats['Contribution_Pct (%)'] = (industry_stats['Total_Contribution'] / total_ret) * 100
        else:
            industry_stats['Contribution_Pct (%)'] = 0.0

        return industry_stats.sort_values(by='Total_Contribution', ascending=False).round(4)

    def generate_attribution_report(self, nav_df: pd.DataFrame, holdings_df: pd.DataFrame, wide_df: pd.DataFrame) -> None:
        """
        调度上述所有归因模块，生成综合归因战报并打印
        """

        # 1. 拆解 Alpha 与 Beta
        print("\n>>> 1. 组合系统性风险与纯净 Alpha 拆解 (CAPM):")
        ab_metrics = self.regress_alpha_beta(nav_df)
        for k, v in ab_metrics.items():
            print(f"   - {k}: {v}")

        # 2. 上下行捕获分析
        print("\n>>> 2. 组合牛熊捕获能力分析 (Capture Ratios):")
        capture_metrics = self.calculate_capture_ratios(nav_df)
        for k, v in capture_metrics.items():
            print(f"   - {k}: {v}")
            
        if capture_metrics.get('Down-Market Capture Ratio (下行捕获率)', 1) < 1:
            print(" 评价: 策略在熊市具有防御性 (下行捕获率 < 1)，跌幅小于大盘。")
        if capture_metrics.get('Up-Market Capture Ratio (上行捕获率)', 0) > 1:
            print(" 评价: 策略在牛市具有高弹性 (上行捕获率 > 1)，涨幅超越大盘。")

        # 3. 行业收益贡献分解
        print("\n>>> 3. 组合行业配置与收益贡献分解 (Industry Attribution):")
        industry_df = self.attribute_holdings_by_industry(holdings_df, wide_df)
        if not industry_df.empty:
            print(industry_df.to_markdown(index=False))
        else:
            print(" 缺少行业映射字段，无法进行行业收益拆解。")