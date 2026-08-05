# 1. 导入 ssl 并打补丁
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

# 2. 终极安全拦截函数
def safe_get_stock_list(*args, **kwargs):
    print("\n检测到通达信底层脏数据，正在启用安全模式直接拉取股票列表")
    api = TdxHq_API(heartbeat=False) 

    connected = False
    for host in hq_hosts:
        name, ip, port = host
        try:
            # 尝试连接，设置3秒超时
            if api.connect(ip, port):
                print(f"【系统拦截】成功连接节点: {name} ({ip}:{port})")
                connected = True
                break
        except:
            continue
            
    if not connected:
        raise Exception("所有几十个节点均无法连接，请检查你的网络防火墙是否拦截了 Python 联网")

    data = []
    # 0:深圳sz, 1:上海sh
    for market in [0, 1]: 
        for i in range(25): # 每个市场分批拉取
            res = api.get_security_list(market, i * 1000)
            if res:
                for row in res:
                    row['sse'] = 'sz' if market == 0 else 'sh'
                    row['sec'] = 'stock'
                data.extend(res)
            else:
                break
                
    # 转换为 DataFrame 并进行极其严格的暴力去重
    df = pd.DataFrame(data)
    df = df.dropna(subset=['code']).drop_duplicates(subset=['code'])
    df = df.set_index('code', drop=False)
    
    print(f"【系统拦截】成功拉取并清洗出 {len(df)} 只唯一股票代码！准备启动海量下载...\n")
    return df

# 进行物理级拦截
QATdx.QA_fetch_get_stock_list = safe_get_stock_list
save_tdx.QA_fetch_get_stock_list = safe_get_stock_list

# 3. 正常启动下载程序
if __name__ == '__main__':
    try:
        print("【状态】网络补丁及安全拦截模块加载成功...")
        print("【状态】开始启动全市场数据同步...\n")
        
        # 核心代码：启动下载
        QA.QA_SU_save_stock_day('tdx')
        
        print("\n恭喜！全市场 A 股日线数据下载任务顺利结束！")
        
    except Exception as e:
        print("\n发现错误，程序未能执行到底！错误信息如下：")
        traceback.print_exc()
        
    input("\n=== 程序已结束，请按回车键退出 ===")