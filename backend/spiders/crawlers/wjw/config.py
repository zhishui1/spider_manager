"""
卫健委爬虫配置
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

SPIDER_ID = 'wjw_2026'
SPIDER_NAME = 'wjw'
SPIDER_DISPLAY_NAME = '卫生健康委爬虫'

START_URLS = [
    'https://www.nhc.gov.cn/wjw/zcfg/list.shtml',
]

COLUMN_CONFIGS = {
    1: {'name': '政策法规', 'end_records': 1512},
}

DATA_DIR, FILES_BASE_DIR = ensure_directories(SPIDER_NAME)
DATA_FILE = get_data_file(SPIDER_NAME)

PROXIES = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808',
}

COOKIES = {
    'JSESSIONID': '62238A0E2D791EBDB362AB0741FFC3F4',
    '_yfxkpy_ssid_10006654': '%7B%22_yfxkpy_firsttime%22%3A%221767589608964%22%2C%22_yfxkpy_lasttime%22%3A%221767589608964%22%2C%22_yfxkpy_visittime%22%3A%221767589608964%22%2C%22_yfxkpy_cookie%22%3A%2220260105130648965255573157593039%22%7D',
}
