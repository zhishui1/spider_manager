"""
爬虫基类模块
提供通用爬虫功能，包括两阶段爬取流程、定时调度、状态管理等
"""

import json
import signal
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from .utils import (
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
from ..redis_manager import get_spider_redis_manager
from ..logger import get_spider_logger


class BaseErrorManager:
    """错误管理器基类"""

    def __init__(self, spider_name: str):
        self.spider_name = spider_name
        self.rm = get_spider_redis_manager(spider_name)
        self.logger = get_spider_logger(spider_name)
        self._error_log_file = Path(f'{spider_name}_errors.log')

    def record_error(self, error_type: str, url: str, message: str):
        """记录错误"""
        timestamp = datetime.now().isoformat()
        error_entry = {
            'timestamp': timestamp,
            'type': error_type,
            'url': url,
            'message': message
        }

        try:
            self.logger.error(message, error_type=error_type, url=url)
            with open(self._error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[错误] 记录错误失败: {e}")

    def get_error_count(self) -> int:
        """获取错误数量"""
        return self.rm.get_error_count()

    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """获取最近错误"""
        return self.rm.get_recent_errors(limit)


class BaseCrawler(ABC):
    """
    通用爬虫框架基类

    提供了爬虫的通用功能：
    - 状态管理（运行/暂停/停止）
    - 信号处理（优雅停止）
    - 暂停/恢复功能
    - Redis队列管理
    - 日志记录
    - 定时调度

    子类需要实现：
    - get_column_configs(): 获取栏目配置
    - get_list_url(): 获取列表页URL
    - build_list_params(): 构建列表页请求参数
    - extract_items(): 从响应中提取数据项
    - crawl_detail_page(): 爬取单个详情页
    - get_item_data(): 准备保存的数据
    """

    SPIDER_NAME: str = ''
    SPIDER_DISPLAY_NAME: str = ''
    DATA_FILE: Path = None

    REQUEST_TIMEOUT: int = 10
    RETRY_TIMES: int = 3
    RETRY_DELAY: int = 10
    REQUEST_DELAY: float = 1
    REQUEST_DELAY_MIN: float = 1
    REQUEST_DELAY_MAX: float = 2
    DETAIL_DELAY_MIN: float = 1
    DETAIL_DELAY_MAX: float = 3
    PERPAGE: int = 15

    PROXIES: Dict = {}
    HEADERS: Dict = {}
    HTML_HEADERS: Dict = {}
    COOKIES: Dict = {}
    DOWNLOADABLE_EXTENSIONS: List[str] = []
    PAGE_LINK_EXTENSIONS: List[str] = []
    START_URLS: List[str] = []

    def __init__(self):
        self.spider_name = self.SPIDER_NAME
        self.rm = get_spider_redis_manager(self.spider_name)
        self.logger = get_spider_logger(self.spider_name)
        self.url_manager = self.rm
        self.error_manager = BaseErrorManager(self.spider_name)

        self.is_running = False
        self.should_stop = False
        self.should_pause = False
        self.is_scheduler_running = False
        self.status = 'idle'
        self.current_date_dir = None

        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """信号处理"""
        print(f"\n[信号] 收到信号 {signum}，准备停止爬虫...")
        self.should_stop = True

    def _check_pause(self) -> None:
        """检查暂停状态"""
        while self.should_pause or self.rm.is_paused():
            if self.should_stop:
                break
            time.sleep(1)
            if self.should_stop:
                break

    @abstractmethod
    def get_column_configs(self) -> Dict[int, Dict]:
        """获取栏目配置，子类必须实现"""
        pass

    @abstractmethod
    def get_list_url(self) -> str:
        """获取列表页URL，子类必须实现"""
        pass

    @abstractmethod
    def build_list_params(self, column_id: int, startrecord: int, endrecord: int, perpage: int = 15) -> Tuple[Dict, Dict]:
        """构建列表页请求参数，子类必须实现"""
        pass

    @abstractmethod
    def extract_items(self, response) -> List[Dict]:
        """从响应中提取数据项，子类必须实现"""
        pass

    @abstractmethod
    def crawl_detail_page(self, link_data: Dict[str, Any]) -> Optional[bool]:
        """爬取单个详情页，子类必须实现"""
        pass

    def get_item_data(self, item_id: int, link_data: Dict[str, Any], title: str, content: str, attachments: List[str]) -> Dict:
        """准备保存的数据"""
        return {
            'item_id': item_id,
            'title': title,
            'publish_date': link_data.get('publish_date', ''),
            'url': link_data.get('url', ''),
            'data': self.get_data_dict(link_data, content, attachments)
        }

    @abstractmethod
    def get_data_dict(self, link_data: Dict[str, Any], content: str, attachments: List[str]) -> Dict:
        """获取自定义data字段，子类必须实现"""
        pass

    @abstractmethod
    def create_link_data(self, item: Dict, category: str) -> Dict[str, Any]:
        """从提取的数据项创建链接数据，子类必须实现"""
        pass

    def _is_all_pagination_complete(self) -> bool:
        """检查所有栏目的翻页是否都已完成"""
        for column_id in self.get_column_configs().keys():
            if not self.rm.is_pagination_complete(column_id):
                return False
        return True

    def run(self) -> bool:
        """运行爬虫（两阶段爬取流程）"""
        if self.is_running:
            print('[警告] 爬虫已在运行中')
            return False

        self.is_running = True
        self.should_stop = False
        self.should_pause = False

        try:
            self.rm.set_status('running', {'started_at': datetime.now().isoformat()})
            self.logger.info(f'{self.spider_name} 爬虫启动')

            if self._is_all_pagination_complete() and self.rm.get_links_queue_size() == 0:
                self.logger.info('所有栏目翻页已完成且无待爬取链接，进入每日定时爬取模式')
                self._start_scheduler()
                return True

            if self.rm.has_incomplete_pagination(self.get_column_configs()):
                self.logger.info('发现未完成的翻页，开始收集链接...')
                self._collect_links_phase()

            if self.should_stop:
                self.logger.info('用户停止爬虫')
                return True

            if self.rm.has_pending_links():
                self.logger.info(f'发现待爬取的详情链接，开始爬取详情...')
                self._crawl_details_phase()
            else:
                self.logger.info('没有待爬取的详情链接')

            if not self.should_stop:
                self.rm.set_status('stopped', {
                    'stopped_at': datetime.now().isoformat(),
                    'reason': 'completed',
                    'links_collected': self.rm.get_visited_count(),
                    'details_crawled': self.rm.get_crawled_count()
                })
                self.logger.info('全部爬取完成')

                if self._is_all_pagination_complete() and self.rm.get_links_queue_size() == 0:
                    self.logger.info('所有栏目已完成且队列为空，自动启动定时调度器...')
                    self._start_scheduler()
                else:
                    self.logger.info('爬取完成，等待手动启动')
            return True

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f'严重错误: {error_msg}', error_type='fatal_error', url='crawler')
            self.rm.set_status('error', {'error': error_msg})
            return False

        finally:
            self.is_running = False
            self._stop_scheduler()
            if self.should_stop:
                self.rm.set_status('stopped', {
                    'stopped_at': datetime.now().isoformat(),
                    'reason': 'user_stopped',
                    'links_collected': self.rm.get_visited_count(),
                    'details_crawled': self.rm.get_crawled_count()
                })
                self.logger.info('爬虫已停止')

    def stop(self) -> None:
        """停止爬虫"""
        self.should_stop = True

    def pause(self) -> None:
        """暂停爬虫"""
        self.should_pause = True
        self.rm.set_paused(True)
        self.rm.set_status('paused', {})

    def resume(self) -> None:
        """恢复爬虫"""
        self.should_pause = False
        self.rm.set_paused(False)
        self.rm.set_status('running', {'resumed_at': datetime.now().isoformat()})

    def _collect_links_phase(self) -> int:
        """阶段1：收集详情页链接
        
        Returns:
            int: 收集到的链接总数
        """
        total_links = 0
        for column_id, config in self.get_column_configs().items():
            if self.should_stop:
                break

            if self.rm.is_pagination_complete(column_id):
                self.logger.info(f'栏目 {config["name"]} 已完成，跳过')
                continue

            category = config['name']
            end_records = config['end_records']

            self.logger.info(f'开始收集栏目: {category}')
            self.rm.set_status('running', {
                'current_category': category,
                'progress': f'收集 {category} 的链接'
            })

            new_links = self._collect_column_links(column_id, category, end_records)
            total_links += new_links

            self.rm.set_pagination_complete(column_id, True)
            self.logger.info(f'栏目 {category} 链接收集完成，新增 {new_links} 个链接')
        
        return total_links

    def _collect_column_links(self, column_id: int, category: str, end_records: int, 
                               stop_on_duplicates: bool = False, max_duplicates: int = 100,
                               force_restart: bool = False) -> int:
        """收集单个栏目的详情页链接
        
        Args:
            column_id: 栏目ID
            category: 栏目名称  
            end_records: 结束记录数
            stop_on_duplicates: 是否在连续重复后停止
            max_duplicates: 最大连续重复数
            force_restart: 是否强制从第一页开始
        """
        startrecord = 0 if force_restart else self.rm.get_last_pagination_page(column_id)
        endrecord = startrecord
        perpage = self.PERPAGE

        self.logger.info(f'栏目 {category} 从第 {startrecord // perpage + 1} 页开始')
        
        consecutive_duplicates = 0
        consecutive_empty = 0
        total_new_links = 0

        while stop_on_duplicates or endrecord < end_records:
            if self.should_stop:
                break

            self._check_pause()
            if self.should_stop:
                break
            
            if stop_on_duplicates and consecutive_duplicates >= max_duplicates:
                self.logger.info(f'栏目 {category} 连续{max_duplicates}个重复，停止翻页')
                break

            startrecord = endrecord
            endrecord = min(endrecord + perpage, end_records)
            links_count = 0
            items_count = 0

            params, data = self.build_list_params(column_id, startrecord, endrecord, perpage)

            try:
                response = request_post_with_retry(
                    self.get_list_url(),
                    data=data,
                    params=params,
                    headers=self.HEADERS,
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
                else:
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

            if not stop_on_duplicates:
                self.rm.set_last_pagination_page(column_id, endrecord)

            if self.should_stop:
                break

            random_delay(self.REQUEST_DELAY_MIN, self.REQUEST_DELAY_MAX)

            if stop_on_duplicates:
                self.logger.info(f'[入队] 栏目 {category} 第{startrecord // perpage + 1}页: {links_count} 个新链接')
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
                current_page = startrecord // perpage + 1
                total_pages = (end_records + perpage - 1) // perpage
                self.logger.link_collection(category, current_page, total_pages, items_count, links_count)

        return total_new_links

    def _crawl_details_phase(self) -> None:
        """阶段2：从队列爬取详情页"""
        total_to_crawl = self.rm.get_links_queue_size() + self.rm.get_details_crawled()
        crawled_count = self.rm.get_details_crawled()

        self.logger.info(f'待爬取 {self.rm.get_links_queue_size()} 条详情，总计 {total_to_crawl} 条')

        consecutive_errors = 0

        while self.rm.has_pending_links() and not self.should_stop:
            self._check_pause()
            if self.should_stop:
                break

            link_data = self.rm.pop_from_links_queue()
            if not link_data:
                break

            url = link_data.get('url')
            if self.rm.is_url_crawled(url):
                self.logger.info(f'已爬取过，跳过: {url}')
                continue

            success = self.crawl_detail_page(link_data)

            if success is True:
                self.rm.mark_url_crawled(url)
                crawled_count = self.rm.increment_details_crawled()
                self.logger.info(f'详情爬取进度: {crawled_count}/{total_to_crawl}')
                consecutive_errors = 0
            elif success is None:
                crawled_count = self.rm.increment_details_crawled()
                self.logger.info(f'详情爬取进度（无内容跳过）: {crawled_count}/{total_to_crawl}')
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                if consecutive_errors >= 100:
                    self.logger.error(f'连续{consecutive_errors}次爬取失败，停止爬虫', error_type='too_many_errors', url=url)
                    self.rm.set_status('stopped', {
                        'stopped_at': datetime.now().isoformat(),
                        'reason': 'too_many_errors',
                        'error_url': url,
                        'links_collected': self.rm.get_visited_count(),
                        'details_crawled': self.rm.get_crawled_count()
                    })
                    break
                self.logger.error(f'爬取失败，将URL放回队列重试: {url}', error_type='detail_failed', url=url)
                self.rm.push_to_links_queue(link_data)
                self.logger.info(f'爬取继续，剩余 {self.rm.get_links_queue_size()} 条待爬取')

    def download_attachments(self, hrefs: List[str], item_dir: Path, item_id: int, base_url: str = '') -> List[str]:
        """下载附件文件"""
        saved_paths = []
        file_index = 2
        downloaded_urls = set()

        for href in hrefs:
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

            if base_url:
                dl_url = parse.urljoin(base_url, href)
            else:
                dl_url = href

            if dl_url in downloaded_urls:
                continue
            downloaded_urls.add(dl_url)

            saved_path = utils_download_file(dl_url, item_dir, f'{item_id}_{file_index}')
            if saved_path:
                saved_paths.append(saved_path)
                self.logger.info(f'[下载] 附件保存成功: {saved_path}')
                file_index += 1
            time.sleep(0.5)

        return saved_paths

    def save_item_data(self, data: Dict[str, Any]) -> None:
        """保存数据项到JSONL文件"""
        with open(self.DATA_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

    def _start_scheduler(self) -> None:
        """启动定时调度器（每天上午8点执行）"""
        import schedule

        if self.is_scheduler_running:
            self.logger.info('调度器已在运行中，跳过启动')
            return

        def job():
            if self._is_all_pagination_complete() and self.rm.get_links_queue_size() == 0:
                self.logger.info('所有栏目已完成且队列为空，进入每日定时爬取模式')
                self._scheduled_crawl_links()
            elif self.rm.get_links_queue_size() > 0:
                self.logger.info('发现待爬取链接，跳过定时爬取，开始爬取详情...')
                self._crawl_details_phase()
            else:
                self.logger.info('还有未完成的翻页，跳过定时爬取')

        self.is_scheduler_running = True
        schedule.every().day.at('08:00').do(job)
        self.logger.info('定时调度器已启动，每天上午8点执行')

        while not self.should_stop and self.is_scheduler_running:
            schedule.run_pending()
            time.sleep(60)

        self.is_scheduler_running = False
        self.logger.info('定时调度器已停止')

    def _stop_scheduler(self) -> None:
        """停止定时调度器"""
        self.is_scheduler_running = False
        self.logger.info('定时调度器已停止')

    def _scheduled_crawl_links(self) -> None:
        """定时爬取链接：从第一页开始翻页，连续100个重复后停止，复用已有方法"""
        self.logger.info('开始定时爬取链接...')
        self.rm.set_status('running', {'started_at': datetime.now().isoformat()})

        self.current_date_dir = None

        total_new_links = 0
        for column_id, config in self.get_column_configs().items():
            if self.should_stop:
                break

            category = config['name']
            self.logger.info(f'开始收集栏目: {category}')
            self.rm.set_status('running', {
                'current_category': category
            })

            new_links = self._collect_column_links(
                column_id=column_id,
                category=category,
                end_records=999999,
                stop_on_duplicates=True,
                max_duplicates=100,
                force_restart=True
            )
            total_new_links += new_links
            self.logger.info(f'[翻页] 栏目 {category} 链接收集完成，新增 {new_links} 个链接')

        self.rm.set_status('running', {
            'new_links': total_new_links
        })
        self.logger.info(f'定时链接爬取完成，新增 {total_new_links} 个链接')

        if self.rm.has_pending_links():
            self.logger.info('发现待爬取的详情链接，开始爬取详情...')
            self._crawl_details_phase()

        self.rm.set_status('stopped', {
            'stopped_at': datetime.now().isoformat(),
            'reason': 'scheduled_completed',
            'links_collected': self.rm.get_visited_count(),
            'details_crawled': self.rm.get_crawled_count()
        })
        self.logger.info('定时爬取全部完成')

    def get_status(self) -> Dict[str, Any]:
        """获取爬虫状态"""
        base_status = self.rm.get_status()
        progress = base_status.get('details', {})

        return {
            'status': base_status.get('status', 'unknown'),
            'running': self.is_running,
            'paused': self.should_pause or base_status.get('details', {}).get('paused') == '1',
            'progress': progress,
            'error_count': self.error_manager.get_error_count(),
            'source': base_status.get('source', 'unknown')
        }


def main():
    """主入口"""
    crawler = BaseCrawler()
    success = crawler.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
