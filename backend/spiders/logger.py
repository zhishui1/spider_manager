"""
爬虫日志管理器 - 将日志写入到logs文件夹
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


class SpiderLogger:
    """爬虫日志管理器"""

    _instances: Dict[str, 'SpiderLogger'] = {}
    _lock = threading.Lock()

    def __new__(cls, spider_type: str):
        if spider_type not in cls._instances:
            with cls._lock:
                if spider_type not in cls._instances:
                    cls._instances[spider_type] = super().__new__(cls)
                    cls._instances[spider_type]._initialized = False
        return cls._instances[spider_type]

    def __init__(self, spider_type: str):
        if self._initialized:
            return
        self.spider_type = spider_type
        self._logs_dir = Path(__file__).resolve().parent.parent.parent / 'logs'
        self._logs_dir.mkdir(exist_ok=True)
        self._log_file = self._logs_dir / f'{spider_type}.log'
        self._log_file.touch(exist_ok=True)
        self._initialized = True
        self._write_lock = threading.Lock()

    def _format_entry(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """格式化日志条目"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'spider_type': self.spider_type
        }
        if kwargs:
            entry['details'] = kwargs
        return entry

    def _write_to_file(self, entry: Dict[str, Any]):
        """写入日志文件"""
        with self._write_lock:
            try:
                with open(self._log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            except Exception as e:
                print(f"[Logger] 写入日志失败: {e}")

    def info(self, message: str, **kwargs):
        """ INFO级别日志 """
        entry = self._format_entry('INFO', message, **kwargs)
        self._write_to_file(entry)
        print(f"[INFO] {message}")

    def warning(self, message: str, **kwargs):
        """ WARNING级别日志 """
        entry = self._format_entry('WARNING', message, **kwargs)
        self._write_to_file(entry)
        print(f"[WARNING] {message}")

    def error(self, message: str, **kwargs):
        """ ERROR级别日志 """
        entry = self._format_entry('ERROR', message, **kwargs)
        self._write_to_file(entry)
        print(f"[ERROR] {message}")

    def debug(self, message: str, **kwargs):
        """ DEBUG级别日志 """
        entry = self._format_entry('DEBUG', message, **kwargs)
        self._write_to_file(entry)
        print(f"[DEBUG] {message}")

    def link_collection(self, category: str, current_page: int, total_pages: int, 
                       items_count: int, links_count: int):
        """记录翻页抓取链接日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': f'栏目: {category} | 当前页: {current_page}/{total_pages} | 抓取: {items_count} | 入队: {links_count}',
            'spider_type': self.spider_type,
            'details': {
                'category': category,
                'current_page': current_page,
                'total_pages': total_pages,
                'items_count': items_count,
                'links_count': links_count,
                'action': 'link_collection'
            }
        }
        self._write_to_file(entry)
        print(f"[翻页] 栏目: {category} | 当前页: {current_page}/{total_pages} | 抓取: {items_count} | 入队: {links_count}")

    def detail_crawl(self, title: str, url: str, crawled_count: int, total_count: int):
        """记录详情页爬取成功日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': f'Crawl success: {title} - {url}',
            'spider_type': self.spider_type,
            'details': {
                'title': title,
                'url': url,
                'crawled_count': crawled_count,
                'total_count': total_count,
                'action': 'detail_crawl'
            }
        }
        self._write_to_file(entry)
        print(f'Crawl success: {title} - {url}')

    def file_download(self, file_name: str, dl_url: str):
        """记录文件下载成功日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': 'INFO',
            'message': f'Download file success: {file_name} - {dl_url}',
            'spider_type': self.spider_type,
            'details': {
                'file_name': file_name,
                'url': dl_url,
                'action': 'file_download'
            }
        }
        self._write_to_file(entry)
        print(f'Download file success: {file_name} - {dl_url}')

    def get_logs(self, limit: int = 100, level: str = None, keyword: str = None) -> List[Dict[str, Any]]:
        """读取日志"""
        if not self._log_file.exists():
            return []

        logs = []
        try:
            with open(self._log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-limit:] if len(lines) > limit else lines

                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        log_entry = json.loads(line)
                        if level and log_entry.get('level', '').upper() != level.upper():
                            continue
                        if keyword and keyword not in log_entry.get('message', ''):
                            continue
                        logs.append(log_entry)
                    except json.JSONDecodeError:
                        logs.append({
                            'message': line,
                            'raw': True,
                            'timestamp': None,
                            'level': 'UNKNOWN'
                        })
        except Exception as e:
            print(f"[Logger] 读取日志失败: {e}")

        return logs

    def clear_logs(self) -> bool:
        """清空日志文件"""
        try:
            with open(self._log_file, 'w', encoding='utf-8') as f:
                f.write('')
            return True
        except Exception as e:
            print(f"[Logger] 清空日志失败: {e}")
            return False


def get_spider_logger(spider_type: str) -> SpiderLogger:
    """获取指定爬虫的日志管理器"""
    return SpiderLogger(spider_type)
