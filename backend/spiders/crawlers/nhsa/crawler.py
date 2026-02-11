"""
国家医保局爬虫核心模块
支持状态上报、Redis队列管理、URL去重和优雅停止
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import parse
from bs4 import BeautifulSoup
import requests
from lxml import etree
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
    PAGE_LINK_EXTENSIONS,
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
    html_to_xpath,
    parse_response,
)
from ...redis_manager import get_spider_redis_manager
from ...logger import get_spider_logger


class NHSACrawler(BaseCrawler):
    """国家医保局爬虫"""

    SPIDER_NAME = SPIDER_NAME
    SPIDER_DISPLAY_NAME = '国家医保局爬虫'
    DATA_FILE = DATA_FILE

    PROXIES = PROXIES
    DOWNLOADABLE_EXTENSIONS = DOWNLOADABLE_EXTENSIONS
    PAGE_LINK_EXTENSIONS = PAGE_LINK_EXTENSIONS
    HEADERS = HEADERS
    HTML_HEADERS = HTML_HEADERS
    COOKIES = {}

    URLS = {
        'list': 'https://www.nhsa.gov.cn/module/web/jpage/dataproxy.jsp',
        'detail': 'https://www.nhsa.gov.cn/art/{article_id}.html',
    }

    def get_column_configs(self) -> Dict[int, Dict]:
        """获取栏目配置"""
        return COLUMN_CONFIGS

    def get_list_url(self) -> str:
        """获取列表页URL"""
        return self.URLS['list']

    def get_detail_url(self, article_id: str) -> str:
        """获取详情页URL"""
        return self.URLS['detail'].format(article_id=article_id)

    def build_list_params(self, column_id: int, startrecord: int, endrecord: int, perpage: int = 15) -> tuple:
        """构建列表页请求参数"""
        params = {
            'startrecord': str(startrecord + 1),
            'endrecord': str(endrecord),
            'perpage': str(perpage),
        }

        data = {
            'col': '1',
            'appid': '1',
            'webid': '1',
            'path': '/',
            'columnid': str(column_id),
            'sourceContentType': '1',
            'unitid': '2464',
            'webname': '国家医疗保障局',
            'permissiontype': '0',
        }

        return params, data

    def extract_items(self, response) -> List[Dict]:
        """从HTML提取数据（国家医保局特有格式）"""
        content = response.text
        record_pattern = r'<record><!\[CDATA\[(.*?)\]\]></record>'
        records = re.findall(record_pattern, content, re.DOTALL)

        data_list = []
        for record in records:
            soup = BeautifulSoup(record, 'html.parser')
            spans = soup.find_all('span')

            if len(spans) >= 4:
                index = spans[0].get_text(strip=True)
                a_tag = spans[1].find('a')
                title = a_tag.get_text(strip=True) if a_tag else spans[1].get_text(strip=True)
                url = a_tag.get('href', '') if a_tag else ''
                url = parse.urljoin('https://www.nhsa.gov.cn/', url)
                document_number = spans[2].get_text(strip=True)
                publish_date = spans[3].get_text(strip=True)

                data_list.append({
                    '索引': index,
                    '标题': title,
                    '发文字号': document_number,
                    '发布日期': publish_date,
                    'URL': url
                })

        return data_list

    def crawl_detail_page(self, link_data: Dict[str, Any]) -> Optional[bool]:
        """爬取单个详情页"""
        url = link_data.get('url')
        category = link_data.get('category', '未知')

        random_delay(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX)

        try:
            item_id = generate_item_id()

            resp = request_get_with_retry(
                url,
                headers=self.HTML_HEADERS,
                proxies=self.PROXIES,
                timeout=self.REQUEST_TIMEOUT,
                retry_times=self.RETRY_TIMES,
                retry_delay=self.RETRY_DELAY,
                logger=self.logger,
                error_recorder=self.error_manager.record_error
            )
            if not resp or resp.status_code != 200:
                self.logger.info(f'无法获取页面: {url}', error_type='request_failed', url=url)
                return None

            html = decode_response(resp)
            doc = html_to_xpath(html)

            title = doc.xpath('//span[@class="mu-sp-2"]/text()')
            title = title[0] if title else link_data.get('title', '无标题')

            content_elements = doc.xpath('//div[@id="zoom"]//text()')
            content = ''.join(content_elements).strip()

            hrefs = doc.xpath('//div[@id="zoom"]//a/@href')
            has_downloadable = False
            for href in hrefs:
                if not href or not isinstance(href, str):
                    continue
                href = href.strip().lower()
                if not href:
                    continue
                is_downloadable = any(ext in href for ext in self.DOWNLOADABLE_EXTENSIONS)
                is_page_link = any(ext in href for ext in self.PAGE_LINK_EXTENSIONS)
                if is_downloadable and not is_page_link:
                    has_downloadable = True
                    break

            if not content and not has_downloadable:
                self.logger.info(f'无内容且无附件，已跳过: {title}', error_type='no_content', url=url)
                return None

            item_dir = ensure_item_dir(self.SPIDER_NAME, item_id)
            if content:
                save_content_to_file(content, item_dir, f'{item_id}_1.txt')

            attachments = self.download_attachments(hrefs, item_dir, item_id, 'https://www.nhsa.gov.cn/')

            data = self.get_item_data(item_id, link_data, title, content, attachments)
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
            'index': link_data.get('index', ''),
            'document_number': link_data.get('document_number', ''),
            'crawled_at': datetime.now().isoformat()
        }

    def create_link_data(self, item: Dict, category: str) -> Dict[str, Any]:
        """从提取的数据项创建链接数据（国家医保局特有格式）"""
        url = item.get('URL', '')
        return {
            'url': url,
            'title': item.get('标题', ''),
            'category': category,
            'index': item.get('索引', ''),
            'document_number': item.get('发文字号', ''),
            'publish_date': item.get('发布日期', ''),
            'collected_at': datetime.now().isoformat()
        }

    def _crawl_column(self, column_id: int, category: str, end_records: int) -> Dict[str, int]:
        """爬取单个栏目（兼容旧接口）"""
        category_count = {}
        startrecord = 0
        endrecord = 0
        perpage = 15
        total_crawled = 0

        while endrecord < end_records:
            if self.should_stop:
                break

            startrecord = endrecord
            endrecord = min(endrecord + perpage, end_records)

            self._check_pause()
            if self.should_stop:
                break

            params = {
                'startrecord': str(startrecord + 1),
                'endrecord': str(endrecord),
                'perpage': str(perpage),
            }

            data = {
                'col': '1',
                'appid': '1',
                'webid': '1',
                'path': '/',
                'columnid': str(column_id),
                'sourceContentType': '1',
                'unitid': '2464',
                'webname': '国家医疗保障局',
                'permissiontype': '0',
            }

            try:
                response = requests.post(
                    self.get_list_url(),
                    params=params,
                    cookies={},
                    headers=self.HEADERS,
                    data=data,
                    timeout=self.REQUEST_TIMEOUT
                )

                if response.status_code != 200:
                    self.logger.error(f'API返回状态码{response.status_code}', error_type='api_error', column_id=str(column_id))
                    continue

                items = self.extract_items(response)
                self.logger.info(f'栏目: {category} - 从 {startrecord + 1} 到 {endrecord}，共 {len(items)} 条')

                for item in items:
                    if self._process_item(item, category, category_count):
                        total_crawled += 1

                    time.sleep(REQUEST_DELAY)

                    if self.should_stop:
                        break

            except Exception as e:
                self.logger.error(f'栏目 {column_id} 爬取失败: {e}', error_type='column_error', column_id=str(column_id))

        return category_count

    def _process_item(self, item: Dict, category: str, category_count: Dict) -> bool:
        """处理单个条目（兼容旧接口）"""
        url = item['URL']

        if self.url_manager.is_duplicate(url):
            self.logger.info(f'链接已存在，跳过: {url}')
            return False

        self._check_pause()
        if self.should_stop:
            return False

        try:
            item_id = generate_item_id()

            resp = request_get_with_retry(
                url,
                headers=self.HTML_HEADERS,
                proxies=self.PROXIES,
                timeout=self.REQUEST_TIMEOUT,
                retry_times=self.RETRY_TIMES,
                retry_delay=self.RETRY_DELAY,
                logger=self.logger,
                error_recorder=self.error_manager.record_error
            )
            if not resp or resp.status_code != 200:
                self.logger.info(f'无法获取页面: {url}', error_type='request_failed', url=url)
                return None

            html = decode_response(resp)
            doc = html_to_xpath(html)

            title = doc.xpath('//span[@class="mu-sp-2"]/text()')
            title = title[0] if title else item['标题']

            content_elements = doc.xpath('//div[@id="zoom"]//text()')
            content = ''.join(content_elements).strip()

            hrefs = doc.xpath('//div[@id="zoom"]//a/@href')
            has_downloadable = False
            for href in hrefs:
                if not href or not isinstance(href, str):
                    continue
                href = href.strip().lower()
                if not href:
                    continue
                is_downloadable = any(ext in href for ext in self.DOWNLOADABLE_EXTENSIONS)
                is_page_link = any(ext in href for ext in self.PAGE_LINK_EXTENSIONS)
                if is_downloadable and not is_page_link:
                    has_downloadable = True
                    break

            if not content and not has_downloadable:
                self.logger.info(f'无内容且无附件，已跳过: {title}', error_type='no_content', url=url)
                return None

            item_dir = ensure_item_dir(self.SPIDER_NAME, item_id)
            if content:
                save_content_to_file(content, item_dir, f'{item_id}_1.txt')

            file_index = 2
            for href in hrefs:
                if not href or not isinstance(href, str):
                    continue
                href = href.strip()
                if not href:
                    continue
                href_lower = href.lower()
                is_downloadable = any(ext in href_lower for ext in self.DOWNLOADABLE_EXTENSIONS)
                is_page_link = any(ext in href_lower for ext in self.PAGE_LINK_EXTENSIONS)
                if not is_downloadable or is_page_link:
                    continue
                dl_url = parse.urljoin('https://www.nhsa.gov.cn/', href)
                saved_path = utils_download_file(dl_url, item_dir, f'{item_id}_{file_index}')
                if saved_path:
                    self.logger.info(f'附件下载成功: {saved_path}')
                    file_index += 1
                time.sleep(0.5)

            data = {
                'item_id': item_id,
                'title': title,
                'publish_date': item['发布日期'],
                'url': url,
                'data': {
                    'category': category,
                    'index': item['索引'],
                    'document_number': item['发文字号'],
                    'crawled_at': datetime.now().isoformat()
                }
            }

            with open(self.DATA_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')

            category_count[category] = category_count.get(category, 0) + 1
            self.logger.info(f'处理成功: {title}')
            return True

        except Exception as e:
            self.logger.error(f'处理失败: {e}', error_type='process_error', url=url)
            return None


def main():
    """主入口"""
    crawler = NHSACrawler()
    success = crawler.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
