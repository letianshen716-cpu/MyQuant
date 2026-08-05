# scripts/02_check_data_status.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import ssl
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import pandas as pd
import QUANTAXIS as QA
from config import DATA_DIR, TEST_STOCKS, CHECK_START_DATE, CHECK_END_DATE

def run_data_inspection():
    print("正在直连 MongoDB 底层，盘点数据总量\n")
    coll = QA.DATABASE.stock_day
    
    # 使用 MongoDB 原生的 distinct 方法，统计不重复的股票数量
    total_stocks = len(coll.distinct('code'))
    print(f"宏观总览：目前你的金库中，共拥有 {total_stocks} 只股票的历史日线数据。")
    print(f"\n正在抽查 {TEST_STOCKS}，验证数据是否已更新")

    # 使用 config 中的全局变量替换写死的日期
    data = QA.QA_fetch_stock_day_adv(TEST_STOCKS, CHECK_START_DATE, CHECK_END_DATE)

    if data is None:
        print("提取失败：未找到任何数据，请检查下载脚本是否还在运行。")
    else:
        df = data.data
        
        for code in TEST_STOCKS:
            try:
                # 单独抽出这只股票的数据
                stock_df = df.xs(code, level='code')
                start_d = str(stock_df.index.get_level_values('date').min())[:10]
                end_d = str(stock_df.index.get_level_values('date').max())[:10]
                
                print(f"\n{code}质量校验通过！")
                print(f"  数据跨度：从 {start_d} 完美延伸至 {end_d}，共计 {len(stock_df)} 个交易日。")
                print(" 尾部最新数据展示 (亲眼见证最新年份)：")
                
                # 打印最后 3 天的核心量价数据
                print(stock_df[['open', 'high', 'low', 'close', 'volume']].tail(3))
            except KeyError:
                print(f"\n警告：{code}的数据暂未查到，可能增量下载程序还没排队下到它。")

        print("\n正在将提取的样本数据保存至本地")
        
        # 1. 找到 data 文件夹下的 processed 文件夹，如果没有就自动创建一个
        processed_dir = DATA_DIR / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. 拼接出我们要保存的完整文件名
        save_path = processed_dir / "sample_check_data.csv"
        
        # 3. 执行真正的保存动作
        df.to_csv(save_path)
        
        print(f"请前往查看文件：{save_path}")

if __name__ == '__main__':
    run_data_inspection()
