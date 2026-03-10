"""
法信-国家法律爬虫启动脚本
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from spiders.crawlers.faxin_guojia.crawler import main

if __name__ == '__main__':
    main()
