import ssl

# 全局 SSL 补丁
ssl.SSLContext.load_default_certs = lambda *args, **kwargs: None
ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()

import QUANTAXIS as QA

def run_download():
    print(">>>  正在下载/更新股票板块数据")
    try:
        QA.QA_SU_save_stock_block('tdx')
    except Exception as e:
        print(f"板块下载异常: {e}")

    try:
        QA.QA_SU_save_financialfiles()
        print("全市场财务文件下载并入库完成！")
    except Exception as e:
        print(f" 财务文件下载异常: {e}")

if __name__ == '__main__':
    run_download()