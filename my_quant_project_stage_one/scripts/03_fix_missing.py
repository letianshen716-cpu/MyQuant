import ssl
import pandas as pd
from datetime import datetime

ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA
import QUANTAXIS.QAFetch.QATdx as QATdx
import QUANTAXIS.QASU.save_tdx as save_tdx
import QUANTAXIS.QAUtil.QADate as QADate

today_str = datetime.now().strftime('%Y-%m-%d')
save_tdx.QA_util_get_real_date = lambda *args, **kwargs: today_str
QADate.QA_util_get_real_date = lambda *args, **kwargs: today_str

def precision_stock_list(*args, **kwargs):
    # 在这里填入你任何查不到的股票代码！
    # sh 代表上海(6开头)，sz 代表深圳(0或3开头)
    target_stocks = [
        {'code': '600519', 'sse': 'sh', 'sec': 'stock'}, # 贵州茅台
        {'code': '601318', 'sse': 'sh', 'sec': 'stock'}  # 中国平安 (之前研究池里的另一只)
    ]
    df = pd.DataFrame(target_stocks)
    return df.set_index('code', drop=False)

# 强行替换框架底层的“全市场获取”函数
QATdx.QA_fetch_get_stock_list = precision_stock_list
save_tdx.QA_fetch_get_stock_list = precision_stock_list


if __name__ == '__main__':
    print("正在向服务器单独请求目标股票的全量数据...")
    # 因为我们骗了框架，它只会去下载我们上面指定的那几只股票
    QA.QA_SU_save_stock_day('tdx')
    print("\n补漏完成！目标股票已入库。")