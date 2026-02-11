"""
国家医保局爬虫启动器
"""
import sys
from pathlib import Path

# 添加backend到Python路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# 导入并运行爬虫
from spiders.crawlers.nhsa.crawler import main

if __name__ == '__main__':
    main()
