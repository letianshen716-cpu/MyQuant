import ssl
import pandas as pd

# 1. 绕过 Windows 系统 SSL 证书校验
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA
# 【关键修改点】直接导入报错发生所在的具体模块 save_tdx
import QUANTAXIS.QASU.save_tdx as save_tdx 

# 2. 核心修复补丁
def patched_stock_list(*args, **kwargs):
    print(">>> [补丁深度生效] 成功拦截 save_tdx 模块中的 pandas 兼容性 Bug！")
    print(">>> 正在从本地数据库提取股票代码...")
    
    # 直接查询本地 MongoDB，获取当前已有日线数据的去重股票代码
    codes = QA.DATABASE.stock_day.distinct('code')
    
    # 加个安全兜底，万一本地真没数据，就给几个测试票
    if not codes:
        print("⚠️ 警告：本地 stock_day 数据库为空，使用默认测试股票列表。")
        codes = ['000001', '600000', '600519', '002001', '300001']
        
    # 伪装成 QUANTAXIS 底层需要的 DataFrame 格式返回
    return pd.DataFrame({'code': codes})

# 3. 实施深度替换 (精准替换掉 save_tdx 里面的那个坏引用)
save_tdx.QA_fetch_get_stock_list = patched_stock_list

if __name__ == '__main__':
    print(">>> 开始拉取除权除息 (xdxr) 数据...")
    
    # 运行下载（此时会自动触发我们的精准补丁，彻底绕过报错）
    QA.QA_SU_save_stock_xdxr('tdx')
    
    print(">>> 下载完成！数据已落盘至 MongoDB。")