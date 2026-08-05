import ssl
import pandas as pd
from pytdx.hq import TdxHq_API
from pytdx.config.hosts import hq_hosts

ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA

def find_missing_a_shares():
    print("正在连接服务器，获取全市场最新 A 股总名单")
    api = TdxHq_API(heartbeat=False)
    for host in hq_hosts:
        try:
            if api.connect(host[1], host[2]): break
        except: pass
    
    server_stocks = []
    # 0 代表深圳市场，1 代表上海市场
    for market in [0, 1]: 
        for i in range(25): 
            res = api.get_security_list(market, i * 1000)
            if res:
                for r in res:
                    code = str(r['code'])
                    # 严谨过滤：剔除指数、基金和废弃代码，只保留正规 A 股 (00, 30, 60, 68 开头)
                    if code.startswith(('00', '30', '60', '68')):
                        server_stocks.append(code)
            else: break
            
    server_set = set(server_stocks)
    print(f"服务器端共检索到纯正 A 股标的：{len(server_set)} 只")

    print("\n正在盘点本地 MongoDB 数据库")
    coll = QA.DATABASE.stock_day
    local_stocks = coll.distinct('code')
    # 同样只过滤出本地的正规 A 股进行公平对比
    local_set = {str(code) for code in local_stocks if str(code).startswith(('00', '30', '60', '68'))}
    print(f"本地数据库中已包含 A 股标的：{len(local_set)} 只")

    print("\n执行集合交叉运算，揪出漏网之鱼")
    missing_stocks = server_set - local_set
    
    if len(missing_stocks) == 0:
        print("\n质检通过！你的本地数据库无懈可击，所有 A 股已全部入库")
    else:
        print(f"\n质检报告：发现 {len(missing_stocks)}只缺失的股票！")
        missing_list = sorted(list(missing_stocks))
        print("以下是缺失的股票代码：")
        print(missing_list)

if __name__ == '__main__':
    find_missing_a_shares()