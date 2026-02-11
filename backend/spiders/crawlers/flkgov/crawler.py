"""
国家法律法规数据库爬虫核心模块
支持状态上报、Redis队列管理、URL去重和优雅停止
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import parse
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .config import (
    COLUMN_CONFIGS,
    DATA_FILE,
    DETAIL_DELAY_MAX,
    DETAIL_DELAY_MIN,
    DOWNLOADABLE_EXTENSIONS,
    HEADERS,
    HTML_HEADERS,
    HEADERS_DOWNLOAD,
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
    decode_response,
)
from ...redis_manager import get_spider_redis_manager
from ...logger import get_spider_logger


class FLKGovCrawler(BaseCrawler):
    """国家法律法规数据库爬虫"""

    SPIDER_NAME = SPIDER_NAME
    SPIDER_DISPLAY_NAME = '国家法律法规数据库爬虫'
    DATA_FILE = DATA_FILE

    PROXIES = PROXIES
    DOWNLOADABLE_EXTENSIONS = DOWNLOADABLE_EXTENSIONS
    PAGE_LINK_EXTENSIONS = PAGE_LINK_EXTENSIONS
    HEADERS = HEADERS
    HTML_HEADERS = HTML_HEADERS
    HEADERS_DOWNLOAD = HEADERS_DOWNLOAD
    COOKIES = {}

    PERPAGE = PERPAGE

    LIST_API = 'https://flk.npc.gov.cn/law-search/search/list'
    DOWNLOAD_API = 'https://flk.npc.gov.cn/law-search/download/pc'

    def get_column_configs(self) -> Dict[int, Dict]:
        """获取栏目配置"""
        return COLUMN_CONFIGS

    def get_list_url(self) -> str:
        """获取列表页API URL"""
        return self.LIST_API

    def build_list_params(self, column_id: int, startrecord: int, endrecord: int, perpage: int = PERPAGE) -> Tuple[Dict, Dict]:
        """构建列表页请求参数（法律法规库使用POST JSON）"""
        params = {}
        data = {
            'searchRange': 1,
            'sxrq': [],
            'gbrq': [],
            'searchType': 2,
            'sxx': [],
            'gbrqYear': [],
            'flfgCodeId': [],
            'zdjgCodeId': [],
            'searchContent': '',
            'orderByParam': {
                'order': '-1',
                'sort': '',
            },
            'pageNum': startrecord // perpage + 1,
            'pageSize': perpage,
        }
        return params, data

    def extract_items(self, response) -> List[Dict]:
        """从API响应提取数据（法律法规数据库特有格式）"""
        try:
            data = response.json()
            rows = data.get('rows', [])
            
            data_list = []
            for item in rows:
                bbbs = item.get('bbbs', '')
                title = item.get('title', '')
                flxz = item.get('flxz', '')
                zdjgName = item.get('zdjgName', '')
                gbrq = item.get('gbrq', '')
                sxrq = item.get('sxrq', '')
                
                encoded_title = parse.quote(title)
                url = f'https://flk.npc.gov.cn/detail?id={bbbs}&fileId=&type=&title={encoded_title}'
                
                data_list.append({
                    'bbbs': bbbs,
                    'title': title,
                    'flxz': flxz,
                    '制定机关': zdjgName,
                    '颁布日期': gbrq,
                    '实施日期': sxrq,
                    'URL': url
                })
            
            return data_list
        except Exception as e:
            self.logger.error(f'解析API响应失败: {e}')
            return []

    def crawl_detail_page(self, link_data: Dict[str, Any]) -> Optional[bool]:
        """爬取单个详情页"""
        url = link_data.get('url')
        bbbs = link_data.get('bbbs', '')
        title = link_data.get('title', '无标题')

        random_delay(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX)

        try:
            item_id = generate_item_id()

            params_download = {
                'format': 'docx',
                'bbbs': bbbs,
            }

            response_dl = requests.get(
                self.DOWNLOAD_API,
                params=params_download,
                headers=self.HEADERS_DOWNLOAD,
                timeout=self.REQUEST_TIMEOUT
            )

            if response_dl.status_code != 200:
                self.logger.info(f'无法获取下载信息: {url}', error_type='request_failed', url=url)
                return None

            dl_json = response_dl.json()
            if dl_json.get('code') != 200:
                self.logger.info(f'下载API返回错误: {dl_json}', error_type='api_error', url=url)
                return None

            dl_url = dl_json.get('data', {}).get('url')
            if not dl_url:
                self.logger.info(f'无下载链接: {title}', error_type='no_content', url=url)
                return None

            response_dl1 = requests.get(dl_url, headers=self.HEADERS_DOWNLOAD, timeout=120)

            if response_dl1.status_code != 200:
                self.logger.info(f'无法下载文件: {url}', error_type='download_failed', url=url)
                return None

            item_dir = ensure_item_dir(self.SPIDER_NAME, item_id)

            saved_path = utils_download_file(
                dl_url, 
                item_dir, 
                f'{item_id}_1',
                timeout=120
            )

            attachments = [saved_path] if saved_path else []

            data = self.get_item_data(item_id, link_data, title, '', attachments)
            self.save_item_data(data)

            crawled_count = self.rm.get_crawled_count()
            total_count = crawled_count + self.rm.get_links_queue_size() + 1
            self.logger.detail_crawl(title, url, crawled_count, total_count)
            return True

        except Exception as e:
            self.logger.error(f'处理失败: {e}', error_type='process_error', url=url)
            return None

    def get_data_dict(self, link_data: Dict[str, Any], content: str, attachments: List[str]) -> Dict:
        """获取自定义data字段"""
        return {
            'category': link_data.get('category', ''),
            'regulation_type': link_data.get('flxz', ''),
            'issuing_body': link_data.get('制定机关', ''),
            'promulgation_date': link_data.get('颁布日期', ''),
            'effective_date': link_data.get('实施日期', ''),
            'crawled_at': datetime.now().isoformat()
        }

    def create_link_data(self, item: Dict, category: str) -> Dict[str, Any]:
        """从提取的数据项创建链接数据"""
        url = item.get('URL', '')
        return {
            'url': url,
            'title': item.get('title', ''),
            'bbbs': item.get('bbbs', ''),
            'category': category,
            'flxz': item.get('flxz', ''),
            '制定机关': item.get('制定机关', ''),
            '颁布日期': item.get('颁布日期', ''),
            '实施日期': item.get('实施日期', ''),
            'publish_date': item.get('颁布日期', ''),
            'collected_at': datetime.now().isoformat()
        }

    def _collect_column_links(self, column_id: int, category: str, end_records: int,
                               stop_on_duplicates: bool = False, max_duplicates: int = 100,
                               force_restart: bool = False) -> int:
        """收集单个栏目的详情页链接（法律法规库特有实现，使用POST API分页）"""
        startrecord = 0 if force_restart else self.rm.get_last_pagination_page(column_id)
        perpage = self.PERPAGE

        self.logger.info(f'栏目 {category} 从第 {startrecord // perpage + 1} 页开始')

        consecutive_duplicates = 0
        consecutive_empty = 0
        total_new_links = 0

        page = startrecord // perpage + 1

        while stop_on_duplicates or (page - 1) * perpage < end_records:
            if self.should_stop:
                break

            self._check_pause()
            if self.should_stop:
                break

            if stop_on_duplicates and consecutive_duplicates >= max_duplicates:
                self.logger.info(f'栏目 {category} 连续{max_duplicates}个重复，停止翻页')
                break

            params, data = self.build_list_params(column_id, startrecord, end_records, perpage)
            data['pageNum'] = page

            try:
                response = requests.post(
                    self.LIST_API,
                    params=params,
                    json=data,
                    headers=self.HEADERS,
                    timeout=self.REQUEST_TIMEOUT
                )

                if response.status_code != 200:
                    self.error_manager.record_error('api_error', str(column_id),
                                                   f'API返回状态码{response.status_code}')
                    consecutive_empty += 1
                    if consecutive_empty >= 3:
                        self.logger.info(f'栏目 {category} 连续3次请求失败，停止翻页')
                        break
                    page += 1
                    continue

                items = self.extract_items(response)
                items_count = len(items)
                links_count = 0

                for item in items:
                    if self.should_stop:
                        break

                    self._check_pause()
                    if self.should_stop:
                        break

                    url = item.get('URL')
                    if self.rm.is_url_visited(url):
                        if stop_on_duplicates:
                            consecutive_duplicates += 1
                            if consecutive_duplicates >= max_duplicates:
                                self.logger.info(f'栏目 {category} 连续{max_duplicates}个重复，停止翻页')
                                break
                        self.logger.info(f'链接已存在，跳过: {url}')
                        continue

                    consecutive_duplicates = 0

                    link_data = self.create_link_data(item, category)

                    self.rm.push_to_links_queue(link_data)
                    self.rm.mark_url_visited(link_data.get('url', ''))
                    links_count += 1
                    total_new_links += 1

                consecutive_empty = 0

            except Exception as e:
                self.logger.error(f'栏目 {column_id} 翻页失败: {e}', error_type='column_error', column_id=str(column_id))
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    self.logger.info(f'栏目 {category} 连续3次异常，停止翻页')
                    break
                page += 1
                continue

            if not stop_on_duplicates:
                self.rm.set_last_pagination_page(column_id, page * perpage)

            if self.should_stop:
                break

            random_delay(self.REQUEST_DELAY_MIN, self.REQUEST_DELAY_MAX)

            if stop_on_duplicates:
                self.logger.info(f'[入队] 栏目 {category} 第{page}页: {links_count} 个新链接')
                if links_count == 0 and items_count > 0:
                    self.logger.info(f'栏目 {category} 无新增链接，停止翻页')
                    break
                if items_count == 0:
                    self.logger.info(f'栏目 {category} 无数据，停止翻页')
                    break
            else:
                if links_count == 0 and items_count > 0:
                    consecutive_duplicates += 1
                    if consecutive_duplicates >= 100:
                        self.logger.info(f'栏目 {category} 连续100页无新增链接，停止翻页')
                        break
                else:
                    consecutive_duplicates = 0
                total_pages = (end_records + perpage - 1) // perpage
                self.logger.link_collection(category, page, total_pages, items_count, links_count)

            page += 1

        return total_new_links


def main():
    """主入口"""
    crawler = FLKGovCrawler()
    success = crawler.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
