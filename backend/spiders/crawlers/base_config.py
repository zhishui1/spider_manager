"""
爬虫通用基础配置
所有爬虫项目共享的通用配置和JSON格式规范
"""

from .utils import (
    BASE_DIR,
    CRAWLERS_DIR,
    DATA_DIR,
    ensure_directories,
    generate_item_id,
    to_relative_path,
)

DATA_FORMAT = {
    'fields': {
        'item_id': '时间戳ID，格式为毫秒级时间戳 (1769153573123)',
        'title': '标题',
        'publish_date': '发布日期，格式为 YYYY-MM-DD',
        'url': '原始页面URL',
        'data': '爬虫特定数据对象，包含以下字段：'
    },
    'data_fields': {
        'category': '分类/栏目名称',
        'index': '索引号',
        'document_number': '发文字号',
        'content': '正文内容',
        'file_paths': '附件文件路径列表',
        'crawled_at': '爬取时间，ISO格式'
    },
    'example': {
        'item_id': 1769153573123,
        'title': '关于进一步加强医疗保障定点医疗机构管理的通知',
        'publish_date': '2026-01-23',
        'url': 'https://www.nhsa.gov.cn/art/2024/1/23/art_45.html',
        'data': {
            'category': '政策法规',
            'index': '1',
            'document_number': '医保发〔2024〕1号',
            'content': '正文内容...',
            'file_paths': ['data/nhsa/nhsa_files/archive/xxx.pdf'],
            'crawled_at': '2026-01-23T10:00:00.000000'
        }
    }
}

REQUEST_TIMEOUT = 10
RETRY_TIMES = 3
RETRY_DELAY = 10
REQUEST_DELAY = 1
REQUEST_DELAY_MIN = 1
REQUEST_DELAY_MAX = 2
DETAIL_DELAY_MIN = 1
DETAIL_DELAY_MAX = 3

HEADERS = {
    'Accept': 'application/xml, text/xml, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'DNT': '1',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

HTML_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

DOWNLOADABLE_EXTENSIONS = [
    '.txt', '.doc', '.docx', '.pdf', '.xls', '.xlsx',
    '.zip', '.rar', '.7z',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'
]

PAGE_LINK_EXTENSIONS = [
    '.html', '.htm', '.shtml', '.asp', '.aspx'
]
