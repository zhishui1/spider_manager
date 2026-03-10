"""
法信-国家法律爬虫配置
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

SPIDER_ID = 'faxin_guojia'
SPIDER_NAME = 'faxin_guojia'
SPIDER_DISPLAY_NAME = '法信-国家法律'

DATA_DIR, FILES_BASE_DIR = ensure_directories(SPIDER_NAME)
DATA_FILE = get_data_file(SPIDER_NAME)

PROXIES = {
    'http': 'http://127.0.0.1:10808',
    'https': 'http://127.0.0.1:10808',
}

COOKIES = {
    'https_waf_cookie': 'ffc3c965-dbb2-4f53a1cee08245c5c54384c26ffe3ffa34ff',
    'faxin_sessionid': 'q22ygmjyg1ntln1i5fury4o1',
    'insert_cookie': '89314150',
    'showUpdate': '2024-12-17',
}

COOKIES_DL = {
    'clx': 'n',
    'sid': 't2d5vn0e3z3nbvc2jvhzh2kq',
    'Hm_lvt_a317640b4aeca83b20c90d410335b70f': '1770603508,1770638665',
    'HMACCOUNT': '8E0AFC09543DDFE4',
    'https_waf_cookie': 'ac128a88-21d0-43cf6cb9fb88638f2068d95edcd593608f76',
    'insert_cookie': '89314150',
    'faxin_sessionid': '2eexxkiigvmhal2zepuohziz',
    'lawapp_web': '2421EA2EE338B005BEE94596896476EE16E0CBC0645469DC9E3C9C34896031783E93E92DE68951837DC183C55477D2729BECE52A6373CB4736699F972CCD69A9450DD299D3CAD981909A5B3264E780574AC761D42ED21C1F79B98771E268E0DBF18A0FBFBBC344832C75A5DF0CCC08A3F440713A0FDEFE66824AB28711939937718B47DA36E5A0C875DFEEF5009D7874B5155413',
}

API_URLS = {
    'list': 'https://www.faxin.cn/v2/api/zyfl/search',
    'detail': 'https://www.faxin.cn/v2/api/zyfl/content',
}

COLUMN_CONFIGS = {
    'main': {
        'name': '国家法律',
        'end_records': 304650,
        'lib': '010106',
    }
}

PERPAGE = 50

START_PAGES = {
    'main': 1,
}

HEADERS_API = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json;charset=UTF-8',
    'DNT': '1',
    'Origin': 'https://www.faxin.cn',
    'Referer': 'https://www.faxin.cn/v2/flfg/gjfl/list.html',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

HEADERS_DL = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/json;charset=UTF-8',
    'DNT': '1',
    'Origin': 'https://www.faxin.cn',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}
