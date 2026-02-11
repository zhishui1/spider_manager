"""
卫健委爬虫启动器
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from spiders.crawlers.wjw.crawler import main

if __name__ == '__main__':
    main()
