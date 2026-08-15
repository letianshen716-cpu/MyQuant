"""
Script 01: 初始化动态目录树与环境测试
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, MONGO_URI

def main():
    
    for directory in [RAW_DATA_DIR, PROCESSED_DATA_DIR, REPORTS_DIR]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[+] 新建系统目录: {directory.relative_to(directory.parent.parent)}")
        else:
            print(f"[*] 目录已就绪: {directory.relative_to(directory.parent.parent)}")
            
    print(f"\n[*] 数据库核心配置项: {MONGO_URI}")

if __name__ == "__main__":
    main()