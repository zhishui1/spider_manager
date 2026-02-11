"""
测试普通爬取使用 archive 目录
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from spiders.crawlers.nhsa.crawler import NHSACrawler
from spiders.crawlers.nhsa.config import FILES_DIR, ARCHIVE_DIR

def test_archive_directory():
    """测试普通爬取使用 archive 目录"""
    print("=" * 50)
    print("测试普通爬取使用 archive 目录")
    print("=" * 50)

    crawler = NHSACrawler()
    crawler.current_date_dir = None

    print(f"\n1. 目录配置:")
    print(f"   FILES_DIR = {FILES_DIR}")
    print(f"   ARCHIVE_DIR = {ARCHIVE_DIR}")

    print(f"\n2. 目录是否存在:")
    print(f"   FILES_DIR 存在: {FILES_DIR.exists()}")
    print(f"   ARCHIVE_DIR 存在: {ARCHIVE_DIR.exists()}")

    print(f"\n3. 模拟普通爬取下载文件（无current_date_dir）:")
    crawler.current_date_dir = None
    test_filename = "普通爬取_测试文件.pdf"

    if crawler.current_date_dir and crawler.current_date_dir.exists():
        file_path = crawler.current_date_dir / crawler._sanitize_filename(test_filename)
        print(f"   使用日期目录: {file_path}")
    else:
        file_path = ARCHIVE_DIR / crawler._sanitize_filename(test_filename)
        print(f"   使用 archive 目录: {file_path}")

    print(f"\n4. 目录结构:")
    print(f"   nhsa_files/")
    print(f"   ├── archive/          # 普通爬取附件")
    print(f"   └── 2026-01-23/       # 定时爬取附件（增量）")

    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)

if __name__ == '__main__':
    test_archive_directory()
