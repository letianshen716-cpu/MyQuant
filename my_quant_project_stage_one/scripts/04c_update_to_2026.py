import ssl
def _patched_context(*args, **kwargs):
    return ssl._create_unverified_context()
ssl.create_default_context = _patched_context

import traceback
import pandas as pd
from pytdx.hq import TdxHq_API
from pytdx.config.hosts import hq_hosts
import QUANTAXIS as QA
import QUANTAXIS.QAFetch.QATdx as QATdx
import QUANTAXIS.QASU.save_tdx as save_tdx

def safe_get_stock_list(*args, **kwargs):
    api = TdxHq_API(heartbeat=False)
    for host in hq_hosts:
        name, ip, port = host
        try:
            if api.connect(ip, port):
                break
        except:
            continue
    data = []
    for market in [0, 1]: 
        for i in range(25): 
            res = api.get_security_list(market, i * 1000)
            if res:
                for row in res:
                    row['sse'] = 'sz' if market == 0 else 'sh'
                    row['sec'] = 'stock'
                data.extend(res)
            else:
                break
    df = pd.DataFrame(data)
    df = df.dropna(subset=['code']).drop_duplicates(subset=['code'])
    df = df.set_index('code', drop=False)
    return df

QATdx.QA_fetch_get_stock_list = safe_get_stock_list
save_tdx.QA_fetch_get_stock_list = safe_get_stock_list

def force_update_calendar():
    df = QATdx.QA_fetch_get_index_day('000001', '1990-01-01', '2026-12-31')
    
    if df is not None and not df.empty:
        dates = df['date'].unique().tolist()
        print(f"【状态】成功抓取到 {len(dates)} 个真实交易日！最新日历已自动对接至: {dates[-1]}")
    
        coll = QA.DATABASE.trade_date
        coll.drop() # 删掉旧日历
        date_list = [{'trade_date': str(d)[:10], 'exchange_id': 'XSHG'} for d in dates]
        coll.insert_many(date_list)
    else:
        raise Exception("日历抓取失败，请检查网络！")

if __name__ == '__main__':
    try:
        # 第一步：打通并强制更新日历
        force_update_calendar()
        
        print("日历已更新，正在启动全市场增量下载 (补齐 2022~2026 数据)")
        # 第二步：启动增量更新
        QA.QA_SU_save_stock_day('tdx')

        
    except Exception as e:
        print("\n发现错误：")
        traceback.print_exc()
        
    input("\n=== 程序已结束，请按回车键退出 ===")