"""
Script 05: 交互式策略绩效可视化看板 (Streamlit)
读取回测产出的 CSV 文件，提供多维度绩效指标、动态净值曲线与持仓明细的交互式展示
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config.settings import PROCESSED_DATA_DIR
except ImportError:
    PROCESSED_DATA_DIR = Path("data/processed")

st.set_page_config(
    page_title="MyQuant 策略回测绩效看板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_backtest_data():
    """读取回测落盘数据并进行基础清洗"""
    nav_file = PROCESSED_DATA_DIR / "backtest_monthly_nav.csv"
    holdings_file = PROCESSED_DATA_DIR / "backtest_holdings_records.csv"
    metrics_file = PROCESSED_DATA_DIR / "backtest_performance_metrics.csv"

    if not (nav_file.exists() and holdings_file.exists() and metrics_file.exists()):
        return None, None, None

    df_nav = pd.read_csv(nav_file)
    df_nav['date'] = pd.to_datetime(df_nav['date'])
    
    df_holdings = pd.read_csv(holdings_file)
    df_holdings['date'] = pd.to_datetime(df_holdings['date'])
    df_holdings['code'] = df_holdings['code'].astype(str).str.zfill(6)
    
    df_metrics = pd.read_csv(metrics_file)
    
    return df_nav, df_holdings, df_metrics


df_nav, df_holdings, df_metrics = load_backtest_data()

if df_nav is None:
    st.error(f"检查 {PROCESSED_DATA_DIR} 目录下是否已生成对应的 CSV 文件。")
    st.stop()

st.sidebar.title("📈 MyQuant 仪表盘")
st.sidebar.markdown("---")

# 年份过滤
min_year = df_nav['date'].dt.year.min()
max_year = df_nav['date'].dt.year.max()
selected_years = st.sidebar.slider(
    "回测区间 (年份)", 
    min_value=min_year, 
    max_value=max_year, 
    value=(min_year, max_year)
)

# 过滤数据
mask = (df_nav['date'].dt.year >= selected_years[0]) & (df_nav['date'].dt.year <= selected_years[1])
df_nav_filtered = df_nav.loc[mask].copy()

# 重置净值起点为 1.0
if not df_nav_filtered.empty:
    df_nav_filtered['portfolio_nav'] = df_nav_filtered['portfolio_nav'] / df_nav_filtered['portfolio_nav'].iloc[0]
    df_nav_filtered['benchmark_nav'] = df_nav_filtered['benchmark_nav'] / df_nav_filtered['benchmark_nav'].iloc[0]



st.title("多因子选股策略综合绩效看板")
st.markdown("该看板基于第四阶段回测引擎输出的标准化数据生成。支持净值时序对比、回撤跟踪及持仓下钻分析。")

# 提取最新的性能指标 (以等权最优模型或最后一行数据为例)
if not df_metrics.empty:
    st.subheader("📊 核心绩效指标 (全样本)")
    
    # 优先展示包含等权或第一行记录的指标
    best_metrics = df_metrics.iloc[0].to_dict()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("年化收益率 (CAGR)", f"{best_metrics.get('Annualized Return (CAGR)', 0) * 100:.2f}%")
    col2.metric("基准年化收益", f"{best_metrics.get('Benchmark CAGR', 0) * 100:.2f}%")
    col3.metric("最大回撤 (MDD)", f"{best_metrics.get('Max Drawdown (MDD)', 0) * 100:.2f}%", delta_color="inverse")
    col4.metric("夏普比率 (Sharpe)", f"{best_metrics.get('Sharpe Ratio', 0):.2f}")
    col5.metric("月度胜率", f"{best_metrics.get('Monthly Win Rate', 0) * 100:.2f}%")
    
    with st.expander("查看全维度指标评估矩阵"):
        st.dataframe(df_metrics, use_container_width=True)

st.markdown("---")


tab1, tab2, tab3 = st.tabs(["📈 累计净值与回撤", "📊 收益分布分析", "💼 历史持仓明细"])

with tab1:
    col_chart1, col_chart2 = st.columns([7, 3])
    
    with col_chart1:
        st.subheader("投资组合 vs 基准 累计净值曲线")
        fig_nav = go.Figure()
        fig_nav.add_trace(go.Scatter(x=df_nav_filtered['date'], y=df_nav_filtered['portfolio_nav'], mode='lines', name='多因子组合净值', line=dict(color='red', width=2)))
        fig_nav.add_trace(go.Scatter(x=df_nav_filtered['date'], y=df_nav_filtered['benchmark_nav'], mode='lines', name='全市场基准净值', line=dict(color='blue', width=2, dash='dash')))
        fig_nav.update_layout(height=450, hovermode="x unified", legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01))
        st.plotly_chart(fig_nav, use_container_width=True)
        
    with col_chart2:
        st.subheader("动态回撤跟踪")
        # 计算过滤区间的动态回撤
        rolling_max = df_nav_filtered['portfolio_nav'].cummax()
        drawdown = (df_nav_filtered['portfolio_nav'] - rolling_max) / rolling_max
        
        fig_dd = px.area(x=df_nav_filtered['date'], y=drawdown, labels={'x': '日期', 'y': '回撤幅度'})
        fig_dd.update_traces(fillcolor='rgba(255, 0, 0, 0.2)', line=dict(color='red', width=1))
        fig_dd.update_yaxes(tickformat=".1%")
        fig_dd.update_layout(height=450)
        st.plotly_chart(fig_dd, use_container_width=True)

with tab2:
    col_dist1, col_dist2 = st.columns(2)
    
    with col_dist1:
        st.subheader("月度收益率分布 (Histogram)")
        fig_hist = px.histogram(df_nav_filtered, x="portfolio_net_return", nbins=30, marginal="box", opacity=0.7)
        fig_hist.update_layout(xaxis_title="月度净收益率", yaxis_title="频数")
        st.plotly_chart(fig_hist, use_container_width=True)
        
    with col_dist2:
        st.subheader("策略超额收益 (vs 基准)")
        fig_bar = go.Figure()
        colors = ['red' if val > 0 else 'green' for val in df_nav_filtered['excess_return']]
        fig_bar.add_trace(go.Bar(x=df_nav_filtered['date'], y=df_nav_filtered['excess_return'], marker_color=colors))
        fig_bar.update_layout(xaxis_title="日期", yaxis_title="超额收益", yaxis_tickformat=".2%")
        st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.subheader("截面持仓明细溯源")
    
    available_dates = df_holdings['date'].dt.date.unique()
    available_dates.sort()
    
    if len(available_dates) > 0:
        selected_date = st.selectbox("选择调仓截面日期", available_dates, index=len(available_dates)-1)
        
        holdings_slice = df_holdings[df_holdings['date'].dt.date == selected_date].copy()
        holdings_slice = holdings_slice.sort_values(by='weight', ascending=False).reset_index(drop=True)
        
        st.write(f"**{selected_date}** 调仓截面共持有 **{len(holdings_slice)}** 只股票。")
        
        # 格式化显示
        display_df = holdings_slice.copy()
        display_df['weight'] = display_df['weight'].apply(lambda x: f"{x*100:.2f}%")
        display_df['ret_next_month'] = display_df['ret_next_month'].apply(lambda x: f"{x*100:.2f}%")
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.warning("暂无持仓明细数据。")