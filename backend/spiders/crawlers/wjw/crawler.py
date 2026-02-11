"""
卫健委爬虫核心模块
支持状态上报、Redis队列管理、URL去重和优雅停止
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import parse
from lxml import etree
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .config import (
    COLUMN_CONFIGS,
    COOKIES,
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
    decode_response,
    html_to_xpath,
    parse_response,
    sanitize_filename,
)
from ...redis_manager import get_spider_redis_manager
from ...logger import get_spider_logger


class JWJCrawler(BaseCrawler):
    """卫健委爬虫"""

    SPIDER_NAME = SPIDER_NAME
    SPIDER_DISPLAY_NAME = '卫生健康委爬虫'
    DATA_FILE = DATA_FILE

    PROXIES = PROXIES
    DOWNLOADABLE_EXTENSIONS = DOWNLOADABLE_EXTENSIONS
    PAGE_LINK_EXTENSIONS = PAGE_LINK_EXTENSIONS
    HEADERS = HEADERS
    HTML_HEADERS = HTML_HEADERS
    COOKIES = COOKIES

    PERPAGE = 24

    def get_column_configs(self) -> Dict[int, Dict]:
        """获取栏目配置"""
        return COLUMN_CONFIGS

    def get_list_url(self) -> str:
        """获取列表页URL"""
        return 'https://www.nhc.gov.cn/wjw/zcfg/list.shtml'

    def get_list_url_by_page(self, page: int) -> str:
        """根据页码获取列表页URL"""
        if page == 1:
            return 'https://www.nhc.gov.cn/wjw/zcfg/list.shtml'
        else:
            return f'https://www.nhc.gov.cn/wjw/zcfg/list_{page}.shtml'

    def build_list_params(self, column_id: int, startrecord: int, endrecord: int, perpage: int = 24) -> Tuple[Dict, Dict]:
        """构建列表页请求参数
        
        卫健委使用URL中的页码来分页，不需要构建复杂的请求参数
        """
        params = {}
        data = {}
        return params, data

    def extract_items(self, response) -> List[Dict]:
        """从HTML提取数据（卫健委特有格式）"""
        html = decode_response(response)
        doc = html_to_xpath(html)

        item_titles = doc.xpath('//ul[@class="zxxx_list mt20"]//li/a/@title')
        item_links = doc.xpath('//ul[@class="zxxx_list mt20"]//li/a/@href')
        item_dates = doc.xpath('//ul[@class="zxxx_list mt20"]//li/span[@class="ml"]//text()')

        data_list = []
        for title, link, date in zip(item_titles, item_links, item_dates):
            url = parse.urljoin('https://www.nhc.gov.cn/wjw/zcfg/list.shtml', link)
            data_list.append({
                '标题': title,
                'URL': url,
                '发布日期': date.strip()
            })

        return data_list

    def crawl_detail_page(self, link_data: Dict[str, Any]) -> Optional[bool]:
        """爬取单个详情页"""
        url = link_data.get('url')
        title = link_data.get('title', '无标题')

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

            source_elements = doc.xpath('//div[@class="source"]/span[@class="mr"]//text()')
            source = ''.join(source_elements).replace('来源:', '').strip()

            content_elements = doc.xpath('//div[@id="xw_box"]//p//text()')
            content = ''.join(content_elements).strip()

            download_links = doc.xpath('//div[@id="xw_box"]//a/@href')
            download_names = doc.xpath('//div[@id="xw_box"]//a//text()')
            image_links = doc.xpath('//div[@id="xw_box"]//img/@src')

            if not content and not download_links and not image_links:
                self.logger.info(f'无内容且无附件，已跳过: {title}', error_type='no_content', url=url)
                return None

            item_dir = ensure_item_dir(self.SPIDER_NAME, item_id)
            if content:
                save_content_to_file(content, item_dir, f'{item_id}_1.txt')

            attachments = self.download_attachments_and_images(download_links, download_names, image_links, item_dir, item_id, url)

            data = self.get_item_data(item_id, link_data, title, content, attachments)
            self.save_item_data(data)

            crawled_count = self.rm.get_crawled_count()
            total_count = crawled_count + self.rm.get_links_queue_size() + 1
            self.logger.detail_crawl(title, url, crawled_count, total_count)
            return True

        except Exception as e:
            self.logger.error(f'处理失败: {e}', error_type='process_error', url=url)
            return None

    def download_attachments_and_images(self, hrefs: List[str], names: List[str], image_srcs: List[str], item_dir: Path, item_id: int, base_url: str) -> List[str]:
        """下载附件文件和图片"""
        saved_paths = []
        file_index = 2
        downloaded_urls = set()

        for href, name in zip(hrefs, names):
            if file_index > 40:
                break
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

            dl_url = parse.urljoin(base_url, href)
            if dl_url in downloaded_urls:
                continue
            downloaded_urls.add(dl_url)

            saved_path = utils_download_file(dl_url, item_dir, f'{item_id}_{file_index}')
            if saved_path:
                saved_paths.append(saved_path)
                self.logger.info(f'[下载] 附件保存成功: {saved_path}')
                file_index += 1
            time.sleep(0.5)

        for img_src in image_srcs:
            if file_index > 40:
                break
            if not img_src or not isinstance(img_src, str):
                continue
            img_src = img_src.strip()
            if not img_src:
                continue

            img_ext = Path(img_src).suffix.lower()
            if img_ext not in self.DOWNLOADABLE_EXTENSIONS:
                continue

            img_url = parse.urljoin(base_url, img_src)
            if img_url in downloaded_urls:
                continue
            downloaded_urls.add(img_url)

            saved_path = utils_download_file(img_url, item_dir, f'{item_id}_{file_index}')
            if saved_path:
                saved_paths.append(saved_path)
                self.logger.info(f'[下载] 图片保存成功: {saved_path}')
                file_index += 1
            time.sleep(0.5)

        return saved_paths

    def get_data_dict(self, link_data: Dict[str, Any], content: str, attachments: List[str]) -> Dict:
        """获取自定义data字段"""
        return {
            'category': link_data.get('category', ''),
            'crawled_at': datetime.now().isoformat()
        }

    def create_link_data(self, item: Dict, category: str) -> Dict[str, Any]:
        """从提取的数据项创建链接数据"""
        url = item.get('URL', '')
        return {
            'url': url,
            'title': item.get('标题', ''),
            '类别': category,
            'category': category,
            '发布日期': item.get('发布日期', ''),
            'publish_date': item.get('发布日期', ''),
            'collected_at': datetime.now().isoformat()
        }

    def _collect_column_links(self, column_id: int, category: str, end_records: int,
                               stop_on_duplicates: bool = False, max_duplicates: int = 100,
                               force_restart: bool = False) -> int:
        """收集单个栏目的详情页链接（卫健委特有实现，使用URL分页）"""
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

            url = self.get_list_url_by_page(page)

            try:
                response = request_get_with_retry(
                    url,
                    headers=self.HEADERS,
                    cookies=self.COOKIES,
                    proxies=self.PROXIES,
                    timeout=self.REQUEST_TIMEOUT,
                    retry_times=self.RETRY_TIMES,
                    retry_delay=self.RETRY_DELAY,
                    logger=self.logger,
                    error_recorder=self.error_manager.record_error
                )

                if not response or response.status_code != 200:
                    self.error_manager.record_error('api_error', str(column_id),
                                                   f'API返回状态码{response.status_code if response else "None"}')
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
    crawler = JWJCrawler()
    success = crawler.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
