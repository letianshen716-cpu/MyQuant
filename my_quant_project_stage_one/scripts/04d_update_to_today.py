import ssl
import pandas as pd
from datetime import datetime
import pymongo.collection
from pytdx.hq import TdxHq_API
from pytdx.config.hosts import hq_hosts
import traceback

ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA
import QUANTAXIS.QAFetch.QATdx as QATdx
import QUANTAXIS.QASU.save_tdx as save_tdx
import QUANTAXIS.QAUtil.QADate as QADate

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

def force_update_calendar_and_download():
    today_str = datetime.now().strftime('%Y-%m-%d')
    print(f"\n正在强行重写底层交易日历，目标日期: {today_str} ")
    
    # 强行修改底层时间指针
    save_tdx.QA_util_get_real_date = lambda *args, **kwargs: today_str
    QADate.QA_util_get_real_date = lambda *args, **kwargs: today_str
    
    # 用 Pandas 生成到今天为止的所有工作日
    dates = pd.date_range(start='1990-01-01', end=today_str, freq='B')
    date_strings = [d.strftime('%Y-%m-%d') for d in dates]
    
    # 暴力覆盖 MongoDB 里的旧日历
    coll = QA.DATABASE.trade_date
    coll.drop()
    coll.insert_many([{'trade_date': d, 'exchange_id': 'XSHG'} for d in date_strings])
    QA.QA_SU_save_stock_day('tdx')


if __name__ == '__main__':
    try:
        force_update_calendar_and_download()
    except Exception as e:
        print("\n发现错误：")
        traceback.print_exc()