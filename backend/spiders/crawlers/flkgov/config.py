"""
国家法律法规数据库爬虫配置
"""

from ..base_config import (
    REQUEST_TIMEOUT,
    RETRY_TIMES,
    RETRY_DELAY,
    REQUEST_DELAY,
    REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX,
    DETAIL_DELAY_MIN,
    DETAIL_DELAY_MAX,
    HEADERS,
    HTML_HEADERS,
    DOWNLOADABLE_EXTENSIONS,
    PAGE_LINK_EXTENSIONS,
)
from ..utils import (
    ensure_directories,
    get_data_file,
)

SPIDER_ID = 'flkgov_2026'
SPIDER_NAME = 'flkgov'
SPIDER_DISPLAY_NAME = '国家法律法规数据库爬虫'

TOTAL_PAGES = 1445
PERPAGE = 20

DATA_DIR, FILES_BASE_DIR = ensure_directories(SPIDER_NAME)
DATA_FILE = get_data_file(SPIDER_NAME)

HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json;charset=UTF-8',
    'DNT': '1',
    'Origin': 'https://flk.npc.gov.cn',
    'Referer': 'https://flk.npc.gov.cn/search',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

HTML_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

HEADERS_DOWNLOAD = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

COLUMN_CONFIGS = {
    1: {'name': '法律法规', 'end_records': TOTAL_PAGES * PERPAGE},
}

PROXIES = {}
