"""
Script 02: 自动化历史行情拉取流水线
应用年度数据切片工作流完成样本集入库
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import RAW_DATA_DIR
from src.data_fetcher import DataFetcher

def main():
    
    fetcher = DataFetcher()
    
    # 模拟待拉取池与时间窗
    target_symbols = ["000001", "600000"]
    start_year = 2020
    end_year = 2026
    
    total_records = 0
    for sym in target_symbols:
        print(f"\n[*] 开启标的 {sym} 的时序数据管道")
        
        # 调用年度分批加载机制，避免一键拉取长达数年的高频数据造成内存溢出
        df_market = fetcher.fetch_historical_data_annual_batches(sym, start_year, end_year)
        
        out_path = RAW_DATA_DIR / f"market_daily_{sym}.parquet"
        df_market.to_parquet(out_path, index=False)
        
        chunk_len = len(df_market)
        total_records += chunk_len
        print(f"[{sym}] 落盘完成! 切片合成记录数: {chunk_len}")
        print(f"   => 存储路径: {out_path.name}")

    print(f"历史数据管道运行结束！总计处理 {total_records} 行基础特征。")

if __name__ == "__main__":
    main()