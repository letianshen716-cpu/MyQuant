"""
Script 00: 全市场基础数据下载与更新入口
负责拉取并入库板块分类与全量财务报告数据
"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.settings import BACKTEST_CONFIG
import QUANTAXIS as QA


def download_all_market_data():
    # 1. 下载股票行业板块数据
    try:
        QA.QA_SU_save_stock_block('tdx')
        QA.QA_SU_save_stock_block('ths')
        print(" 股票板块数据已成功更新并入库！")
    except Exception as e:
        print(f" 板块数据更新异常: {e}")

    # 2. 下载上市公司财务数据
    try:
        QA.QA_SU_save_financialfiles()
    except Exception as e:
        print(f" 财务文件下载异常: {e}")


if __name__ == '__main__':
    download_all_market_data()