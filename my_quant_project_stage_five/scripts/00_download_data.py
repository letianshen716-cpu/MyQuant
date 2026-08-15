"""
Script 00: 基础板块与财务数据下载入库
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import QUANTAXIS as QA

def download_all_market_data():
    try:
        QA.QA_SU_save_stock_block('tdx')
        QA.QA_SU_save_stock_block('ths')
    except Exception as e:
        print(f"板块数据更新异常: {e}")

    try:
        QA.QA_SU_save_financialfiles()
    except Exception as e:
        print(f"财务文件下载异常: {e}")

if __name__ == '__main__':
    download_all_market_data()