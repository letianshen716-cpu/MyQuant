import ssl
import traceback
import pandas as pd
from datetime import datetime
from pytdx.hq import TdxHq_API
from pytdx.config.hosts import hq_hosts
import pymongo.collection

import QUANTAXIS as QA
import QUANTAXIS.QAFetch.QATdx as QATdx
import QUANTAXIS.QASU.save_tdx as save_tdx
import QUANTAXIS.QAUtil.QADate as QADate

def _patched_context(*args, **kwargs):
    return ssl._create_unverified_context()
ssl.create_default_context = _patched_context

original_insert_many = pymongo.collection.Collection.insert_many
def safe_insert_many(self, documents, *args, **kwargs):
    if not documents or len(documents) == 0:
        return None  
    return original_insert_many(self, documents, *args, **kwargs)
pymongo.collection.Collection.insert_many = safe_insert_many

def safe_get_stock_list(*args, **kwargs):
    api = TdxHq_API(heartbeat=False)
    for host in hq_hosts:
        try:
            if api.connect(host[1], host[2]): break
        except: pass
    data = []
    for market in [0, 1]: 
        for i in range(25): 
            res = api.get_security_list(market, i * 1000)
            if res:
                for r in res:
                    r['sse'] = 'sz' if market == 0 else 'sh'
                    r['sec'] = 'stock'
                data.extend(res)
            else: break
    df = pd.DataFrame(data).dropna(subset=['code']).drop_duplicates(subset=['code'])
    return df.set_index('code', drop=False)

QATdx.QA_fetch_get_stock_list = safe_get_stock_list
save_tdx.QA_fetch_get_stock_list = safe_get_stock_list

today_str = datetime.now().strftime('%Y-%m-%d')
def force_today(*args, **kwargs):
    return today_str

save_tdx.QA_util_get_real_date = force_today
QADate.QA_util_get_real_date = force_today


if __name__ == '__main__':
    try:
        print("系统级别补丁加载中")
        print(f"已强行修改底层时间引擎，当前识别日期: {today_str}")
        print("已成功安装 MongoDB 空数据防爆拦截器")
        print("开始全量安全下载\n")
        
        # 启动下载！
        QA.QA_SU_save_stock_day('tdx')
        
        print("\n全部股票的历史数据已无缝对接到今天")
        
    except Exception as e:
        print("\n发现错误：")
        traceback.print_exc()
        
    input("\n=== 程序已结束，请按回车键退出 ===")