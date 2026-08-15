"""
Script 05: 策略收益归因分析与可视化看板生成
执行 CAPM 归因、行业贡献拆解，并输出高清机构级风险看板图表
"""
import sys
from pathlib import Path
import warnings
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from config.settings import PROCESSED_DATA_DIR, REPORTS_DIR, WIDE_TABLE_PATH
from src.performance_attributor import PerformanceAttributor

warnings.filterwarnings('ignore')


def plot_risk_dashboard(nav_df: pd.DataFrame, output_path: Path):
    """生成策略风险可视化看板 (含累计净值、水下回撤、月度热力图)"""
    nav_df.index = pd.to_datetime(nav_df.index)

    try:
        plt.style.use('seaborn-v0_8-darkgrid') 
    except OSError:
        try:
            plt.style.use('seaborn-darkgrid')  
        except OSError:
            plt.style.use('ggplot')            
            
    fig, axes = plt.subplots(3, 1, figsize=(14, 18), gridspec_kw={'height_ratios': [2, 1, 1.5]})
    
    x_dates = nav_df.index.to_numpy()
    y_port = nav_df['portfolio_nav'].to_numpy()
    y_bench = nav_df['benchmark_nav'].to_numpy()
    y_excess = nav_df['excess_nav'].to_numpy()
    y_drawdown = nav_df['drawdown'].to_numpy()

    ax1 = axes[0]
    ax1.plot(x_dates, y_port, label='Strategy NAV', color='crimson', linewidth=2)
    ax1.plot(x_dates, y_bench, label='Benchmark NAV', color='steelblue', linewidth=1.5, alpha=0.8)
    ax1.plot(x_dates, y_excess, label='Excess NAV (Alpha)', color='darkorange', linewidth=2, linestyle='--')
    
    ax1.set_title('Strategy vs Benchmark Cumulative NAV', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Cumulative Return', fontsize=12)
    ax1.legend(loc='upper left', fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.6)
   
    ax2 = axes[1]
    ax2.fill_between(x_dates, y_drawdown, 0, color='indianred', alpha=0.4)
    ax2.plot(x_dates, y_drawdown, color='darkred', linewidth=1)
    
    ax2.set_title('Underwater Plot (Drawdown)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Drawdown (%)', fontsize=12)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x*100:.0f}%'))
    ax2.grid(True, linestyle='--', alpha=0.6)

    ax3 = axes[2]
    # 构建 Year-Month 透视表
    nav_df['Year'] = nav_df.index.year
    nav_df['Month'] = nav_df.index.month
    monthly_ret_pivot = nav_df.pivot_table(values='portfolio_net_return', index='Year', columns='Month')
    
    # 将月份索引替换为简写
    month_map = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    monthly_ret_pivot.columns = [month_map.get(c, c) for c in monthly_ret_pivot.columns]
    
    sns.heatmap(monthly_ret_pivot, annot=True, fmt=".2%", cmap="RdYlGn", center=0, ax=ax3, 
                linewidths=0.5, cbar_kws={'label': 'Monthly Return'})
    ax3.set_title('Monthly Return Heatmap', fontsize=14, fontweight='bold')
    ax3.set_ylabel('Year', fontsize=12)
    ax3.set_xlabel('Month', fontsize=12)

    plt.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def generate_final_attribution():

    nav_path = PROCESSED_DATA_DIR / "backtest_monthly_nav.csv"
    holdings_path = PROCESSED_DATA_DIR / "backtest_holdings_records.csv"
    
    if not nav_path.exists() or not holdings_path.exists() or not WIDE_TABLE_PATH.exists():
        print("缺失回测结果文件或大宽表数据")
        return

    # 加载必要数据
    nav_df = pd.read_csv(nav_path, index_col='date', parse_dates=True)
    
    # 强制指定 parse_dates 解析日期，并用 dtype 保留股票代码的前导零字符串格式
    holdings_df = pd.read_csv(holdings_path, parse_dates=['date'], dtype={'code': str})
    
    wide_df = pd.read_parquet(WIDE_TABLE_PATH)
    # 确保 wide_df 的 code 也是字符串类型，防范潜在类型冲突
    wide_df['code'] = wide_df['code'].astype(str).str.zfill(6)

    attributor = PerformanceAttributor(risk_free_rate=0.02, annual_periods=12)
    attributor.generate_attribution_report(nav_df, holdings_df, wide_df)

    dashboard_path = REPORTS_DIR / "05_strategy_risk_dashboard.png"
    plot_risk_dashboard(nav_df, dashboard_path)
    
    print(f"可视化看板已成功生成并保存至: {dashboard_path}")



if __name__ == '__main__':
    generate_final_attribution()