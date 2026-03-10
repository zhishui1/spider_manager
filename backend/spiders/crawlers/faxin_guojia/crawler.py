"""
法信-国家法律爬虫核心模块
支持状态上报、Redis队列管理、URL去重和优雅停止
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import parse
from bs4 import BeautifulSoup
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .config import (
    API_URLS,
    COLUMN_CONFIGS,
    COOKIES,
    COOKIES_DL,
    DATA_FILE,
    DETAIL_DELAY_MAX,
    DETAIL_DELAY_MIN,
    DOWNLOADABLE_EXTENSIONS,
    HEADERS,
    HEADERS_API,
    HEADERS_DL,
    HTML_HEADERS,
    PAGE_LINK_EXTENSIONS,
    PERPAGE,
    PROXIES,
    REQUEST_DELAY,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    RETRY_TIMES,
    SPIDER_NAME,
)
from ..base_crawler import BaseCrawler
from ..utils import (
    generate_item_id,
    random_delay,
    ensure_item_dir,
    save_content_to_file,
    download_file as utils_download_file,
    request_get_with_retry,
    request_post_with_retry,
    decode_response,
)
from ...redis_manager import get_spider_redis_manager
from ...logger import get_spider_logger


class FAXINGUOJIACrawler(BaseCrawler):
    """法信-国家法律爬虫"""

    SPIDER_NAME = SPIDER_NAME
    SPIDER_DISPLAY_NAME = '法信-国家法律'
    DATA_FILE = DATA_FILE

    PROXIES = PROXIES
    DOWNLOADABLE_EXTENSIONS = DOWNLOADABLE_EXTENSIONS
    PAGE_LINK_EXTENSIONS = PAGE_LINK_EXTENSIONS
    HEADERS = HEADERS
    HTML_HEADERS = HTML_HEADERS

    URLS = {
        'list': API_URLS['list'],
        'detail': API_URLS['detail'],
        'base': 'https://www.faxin.cn/v2/flfg/gjfl/content.html',
    }

    PERPAGE = PERPAGE

    def get_column_configs(self) -> Dict[str, Dict]:
        """获取栏目配置"""
        return COLUMN_CONFIGS

    def get_list_url(self) -> str:
        """获取列表页URL"""
        return self.URLS['list']

    def get_detail_url(self, gid: str) -> str:
        """获取详情页URL"""
        return f"{self.URLS['base']}?gid={gid}"

    def _make_list_request(self, column_id: int, startrecord: int, endrecord: int, perpage: int):
        """发起列表页请求（faxin使用JSON body和专用headers）"""
        params, data = self.build_list_params(column_id, startrecord, endrecord, perpage)
        return request_post_with_retry(
            self.get_list_url(),
            data=json.dumps(data),
            params=params,
            cookies=COOKIES,
            headers=HEADERS_API,
            proxies=self.PROXIES,
            timeout=self.REQUEST_TIMEOUT,
            retry_times=self.RETRY_TIMES,
            retry_delay=self.RETRY_DELAY,
            logger=self.logger,
            error_recorder=self.error_manager.record_error
        )

    def build_list_params(self, column_id: int, startrecord: int, endrecord: int, perpage: int = None) -> tuple:
        """构建列表页请求参数"""
        if perpage is None:
            perpage = self.PERPAGE

        config = COLUMN_CONFIGS.get('main', COLUMN_CONFIGS['main'])

        json_data = {
            'searchParams': {
                'shixiao_id': '01',
            },
            'result': [],
            'isAdvSearch': '0',
            'searchType': '1',
            'lib': config.get('lib', '010106'),
            'sort_field': '',
            'size': perpage,
            'page': startrecord // perpage + 1,
        }

        return {}, json_data

    def extract_items(self, response) -> List[Dict]:
        """从API响应提取数据"""
        try:
            json_data = response.json()
            items = json_data.get('data', {}).get('datas', [])
            return items
        except Exception as e:
            self.logger.error(f'解析API响应失败: {e}', error_type='parse_error')
            return []

    def crawl_detail_page(self, link_data: Dict[str, Any]) -> Optional[bool]:
        """爬取单个详情页"""
        gid = link_data.get('gid')
        if not gid:
            self.logger.error('缺少gid参数', error_type='missing_param')
            return None

        url = self.get_detail_url(gid)

        random_delay(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX)

        try:
            item_id = generate_item_id()

            json_data_d = {'gid': gid}

            headers_dl = dict(HEADERS_DL)
            headers_dl['Referer'] = url

            resp = request_post_with_retry(
                self.URLS['detail'],
                data=json.dumps(json_data_d),
                cookies=COOKIES_DL,
                headers=headers_dl,
                proxies=self.PROXIES,
                timeout=self.REQUEST_TIMEOUT,
                retry_times=self.RETRY_TIMES,
                retry_delay=self.RETRY_DELAY,
                logger=self.logger,
                error_recorder=self.error_manager.record_error
            )

            if not resp or resp.status_code != 200:
                self.logger.info(f'无法获取详情: {gid}', error_type='request_failed', url=url)
                return None

            try:
                download_items = resp.json().get('data', {}).get('data', [])
            except Exception:
                self.logger.error(f'解析详情响应失败: {gid}', error_type='parse_error')
                return None

            fulltext = ''
            attachments = []
            downloaded_urls = set()

            for dl_item in download_items:
                allannexEntityList = dl_item.get('allannexEntityList', [])
                item_fulltext = dl_item.get('fulltext', '')

                if item_fulltext:
                    fulltext = self._clean_html_text(item_fulltext)

                for annex in allannexEntityList:
                    d_url = annex.get('url')
                    d_name = annex.get('filename')

                    if d_url and d_url not in downloaded_urls:
                        downloaded_urls.add(d_url)
                        attachments.append({
                            'filename': d_name,
                            'url': d_url
                        })

            item_dir = ensure_item_dir(self.SPIDER_NAME, item_id)

            if fulltext:
                save_content_to_file(fulltext, item_dir, f'{item_id}_1.txt')

            for idx, annex in enumerate(attachments):
                dl_url = annex['url']
                filename = annex['filename']

                if not filename:
                    filename = f'{item_id}_{idx + 2}_attachment'

                saved_path = utils_download_file(
                    dl_url,
                    item_dir,
                    filename,
                    headers=self.HEADERS,
                    proxies=self.PROXIES,
                    timeout=self.REQUEST_TIMEOUT
                )

                if saved_path:
                    annex['saved_path'] = str(saved_path)
                    self.logger.info(f'附件下载成功: {saved_path}')
                    time.sleep(REQUEST_DELAY)

            data = self.get_data_dict(link_data, fulltext, attachments)
            self.save_item_data(data)

            crawled_count = self.rm.get_crawled_count()
            total_count = crawled_count + self.rm.get_links_queue_size() + 1
            self.logger.detail_crawl(link_data.get('title', gid), url, crawled_count, total_count)
            return True

        except Exception as e:
            self.logger.error(f'处理详情页失败: {e}', error_type='process_error', url=url)
            return None

    def _clean_html_text(self, html_content: str) -> str:
        """清理HTML内容"""
        if not html_content:
            return ''

        soup = BeautifulSoup(html_content, 'html.parser')

        for br in soup.find_all('br'):
            br.replace_with('\n')

        for div in soup.find_all('div'):
            div.insert_before('\n')
            div.insert_after('\n')

        text = soup.get_text()
        text = re.sub(r'\n{3,}', '\n\n', text)

        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        text = text.strip()

        return text

    def get_data_dict(self, link_data: Dict[str, Any], content: str, attachments: List[Dict]) -> Dict:
        """获取自定义data字段"""
        attachment_files = []
        for annex in attachments:
            if annex.get('saved_path'):
                filename = os.path.basename(annex['saved_path'])
                attachment_files.append(filename)

        return {
            'fdep': link_data.get('fdep', ''),
            'fwzh': link_data.get('fwzh', ''),
            'gid': link_data.get('gid', ''),
            'shixiao': link_data.get('shixiao', ''),
            'sort': link_data.get('sort', ''),
            'ssrq': link_data.get('ssrq', ''),
            'xiaoli': link_data.get('xiaoli', ''),
            'attachments': attachment_files,
            'crawled_at': datetime.now().isoformat()
        }

    def create_link_data(self, item: Dict, column_key: str) -> Dict[str, Any]:
        """从API数据创建链接数据"""
        return {
            'gid': item.get('gid', ''),
            'title': item.get('title', ''),
            'category': column_key,
            'fdep': item.get('fdep', ''),
            'fwzh': item.get('fwzh', ''),
            'fdate': item.get('fdate', ''),
            'shixiao': item.get('shixiao', ''),
            'sort': item.get('sort', ''),
            'ssrq': item.get('ssrq', ''),
            'xiaoli': item.get('xiaoli', ''),
            'url': self.get_detail_url(item.get('gid', '')),
            'collected_at': datetime.now().isoformat()
        }


def main():
    """主入口"""
    crawler = FAXINGUOJIACrawler()
    success = crawler.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
