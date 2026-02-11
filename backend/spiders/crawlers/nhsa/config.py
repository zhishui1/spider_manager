"""
国家医保局爬虫配置
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

SPIDER_ID = 'nhsa_2026'
SPIDER_NAME = 'nhsa'
SPIDER_DISPLAY_NAME = '国家医保局爬虫'

START_URLS = [
    'https://www.nhsa.gov.cn/col/col104/index.html?uid=2464',
    'https://www.nhsa.gov.cn/col/col105/index.html?uid=2464',
    'https://www.nhsa.gov.cn/col/col109/index.html?uid=2464',
    'https://www.nhsa.gov.cn/col/col110/index.html?uid=2464',
]

COLUMN_CONFIGS = {
    104: {'name': '政策法规', 'end_records': 244},
    105: {'name': '政策解读', 'end_records': 105},
    109: {'name': '通知公告', 'end_records': 267},
    110: {'name': '建议提案', 'end_records': 783},
}

DATA_DIR, FILES_BASE_DIR = ensure_directories(SPIDER_NAME)
DATA_FILE = get_data_file(SPIDER_NAME)

PROXIES = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808',
}

COOKIES = {
    'JSESSIONID': '854C95A63E2F960823250D982D33424C',
}
