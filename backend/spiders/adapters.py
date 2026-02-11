"""
Spider adapters for different crawler types.
提供统一的爬虫控制接口，支持启动、停止、暂停、恢复等操作
"""

import abc
import subprocess
import time
import json
import os
import sys
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from .redis_manager import get_spider_redis_manager, SpiderRedisManager


def count_files_recursive(directory: Path) -> int:
    """递归统计目录下所有文件的数量（包括子文件夹）- 优化版本"""
    if not directory or not directory.exists():
        return 0
    
    def _count_fast(path: Path) -> int:
        count = 0
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file():
                        count += 1
                    elif entry.is_dir():
                        count += _count_fast(Path(entry.path))
        except (PermissionError, OSError):
            pass
        return count
    
    return _count_fast(directory)


def count_file_types(directory: Path) -> Dict[str, int]:
    """统计目录下各类文件的数量，按扩展名分组"""
    file_types: Dict[str, int] = {}
    if not directory or not directory.exists():
        return file_types
    for item in directory.iterdir():
        if item.is_file():
            ext = item.suffix.lower()
            if ext:
                file_types[ext] = file_types.get(ext, 0) + 1
            else:
                file_types['无扩展名'] = file_types.get('无扩展名', 0) + 1
        elif item.is_dir():
            sub_types = count_file_types(item)
            for ext, count in sub_types.items():
                file_types[ext] = file_types.get(ext, 0) + count
    return file_types


class SpiderAdapter(abc.ABC):
    """爬虫适配器基类"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.process = None
        self.status = 'idle'
        self.last_output = ''
        self._crawler_instance = None
        self._redis_manager: Optional[SpiderRedisManager] = None

    @abc.abstractmethod
    def get_name(self) -> str:
        """获取爬虫名称"""
        pass

    @abc.abstractmethod
    def get_type(self) -> str:
        """获取爬虫类型"""
        pass

    @abc.abstractmethod
    def start(self, **kwargs) -> bool:
        """启动爬虫"""
        pass

    @abc.abstractmethod
    def stop(self) -> bool:
        """停止爬虫"""
        pass

    @abc.abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """获取爬虫状态"""
        pass

    @abc.abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """获取爬虫统计信息"""
        pass

    def _get_redis_manager(self) -> SpiderRedisManager:
        """获取Redis管理器"""
        if self._redis_manager is None:
            self._redis_manager = get_spider_redis_manager(self.get_type())
        return self._redis_manager


class NHSASpiderAdapter(SpiderAdapter):
    """国家医保局爬虫适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.script_path = base_dir / 'backend' / 'spiders' / 'crawlers' / 'nhsa' / 'start.py'
        self.data_file = base_dir / 'data' / 'nhsa' / 'nhsa_data.json'
        self.files_dir = base_dir / 'data' / 'nhsa' / 'nhsa_files'
        self._monitor_thread = None
        self._stop_monitoring = False

    def get_name(self) -> str:
        return '国家医保局爬虫'

    def get_type(self) -> str:
        return 'nhsa'

    def _start_monitor_thread(self):
        """启动状态监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_monitoring = False
        self._monitor_thread = threading.Thread(target=self._monitor_status, daemon=True)
        self._monitor_thread.start()

    def _read_output(self):
        """读取并打印爬虫输出"""
        if self.process and self.process.stdout:
            for line in iter(self.process.stdout.readline, ''):
                if self._stop_monitoring:
                    break
                if line:
                    print(f'[Crawler] {line.rstrip()}')

    def _monitor_status(self):
        """监控爬虫状态"""
        output_thread = threading.Thread(target=self._read_output, daemon=True)
        output_thread.start()

        while not self._stop_monitoring:
            try:
                if self.process and self.process.poll() is None:
                    poll_result = self.process.poll()
                    if poll_result is None:
                        self._get_redis_manager().set_status('running', {
                            'pid': self.process.pid,
                            'monitoring': 'true'
                        })
                else:
                    break
            except Exception:
                pass
            time.sleep(2)

        self._stop_monitoring = True

    def _stop_monitor_thread(self):
        """停止监控线程"""
        self._stop_monitoring = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def start(self, **kwargs) -> bool:
        if self.process and self.process.poll() is None:
            return False

        try:
            rm = self._get_redis_manager()
            rm.set_status('starting', {'started_at': datetime.now().isoformat()})

            cmd = [sys.executable, str(self.script_path)]
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            cwd = str(Path(__file__).resolve().parent.parent.parent)

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.status = 'running'
            self._start_monitor_thread()

            rm.set_status('running', {
                'pid': self.process.pid,
                'started_at': datetime.now().isoformat()
            })

            return True

        except Exception as e:
            self.status = 'error'
            self._get_redis_manager().set_status('error', {'error': str(e)})
            return False

    def stop(self) -> bool:
        rm = self._get_redis_manager()
        rm.set_status('stopping', {'stopped_at': datetime.now().isoformat()})

        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                for _ in range(10):
                    if self.process.poll() is not None:
                        break
                    time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self._stop_monitor_thread()
        self.process = None
        self.status = 'idle'

        rm.set_status('stopped', {
            'stopped_at': datetime.now().isoformat()
        })

        return True

    def get_status(self) -> Dict[str, Any]:
        rm = self._get_redis_manager()
        redis_status = rm.get_status()
        last_update = redis_status.get('updated_at')

        process_status = {
            'status': 'idle',
            'running': False,
            'pid': None
        }

        if self.process:
            poll_result = self.process.poll()
            if poll_result is None:
                process_status = {
                    'status': self.status,
                    'running': True,
                    'pid': self.process.pid
                }
            else:
                process_status = {
                    'status': 'idle',
                    'running': False,
                    'pid': None,
                    'exit_code': poll_result
                }

        redis_progress = rm.get_progress()

        combined_status = {
            **process_status,
            'redis_status': redis_status.get('status'),
            'progress': redis_progress,
            'error_count': rm.get_error_count(),
            'links_collected': rm.get_visited_count(),
            'details_crawled': rm.get_crawled_count(),
            'pending_links': rm.get_links_queue_size(),
            'version': redis_status.get('version'),
            'reason': redis_status.get('reason'),
            'last_update': last_update
        }

        if redis_status.get('status') in ['running', 'paused', 'stopping']:
            combined_status['status'] = redis_status.get('status')
        else:
            combined_status['status'] = 'stopped'
        
        combined_status['running'] = redis_status.get('status') == 'running'

        return combined_status

    def get_phase(self) -> str:
        """获取当前爬取阶段"""
        return self._get_redis_manager().get_phase()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（优先从Redis读取，后台定时刷新）"""
        rm = self._get_redis_manager()
        
        stats = rm.get_stats()
        if stats and stats.get('total_items', 0) > 0:
            return stats
        
        stats = {
            'total_items': 0,
            'categories': {},
            'date_range': {
                'earliest': None,
                'latest': None
            },
            'file_count': 0,
            'file_types': {},
            'last_update': None
        }
        
        if self.data_file.exists():
            try:
                total = 0
                categories = {}
                dates = []
                
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        total += 1
                        try:
                            data = json.loads(line)
                            category = data.get('类别', '未知')
                            categories[category] = categories.get(category, 0) + 1
                            publish_date = data.get('发布日期')
                            if publish_date:
                                dates.append(publish_date)
                        except (json.JSONDecodeError, KeyError):
                            pass

                stats['total_items'] = total
                stats['categories'] = categories
                if dates:
                    stats['date_range']['earliest'] = min(dates)
                    stats['date_range']['latest'] = max(dates)
                
                stats['last_update'] = datetime.fromtimestamp(
                    self.data_file.stat().st_mtime
                ).isoformat()
            except Exception:
                pass

        try:
            if self.files_dir.exists():
                stats['file_count'] = count_files_recursive(self.files_dir)
                stats['file_types'] = count_file_types(self.files_dir)
        except Exception:
            pass

        crawled_count = rm.get_details_crawled()
        stats['crawled_count'] = crawled_count
        stats['visited_urls'] = rm.get_visited_count()

        rm.set_stats(stats)
        
        return stats

    def _refresh_stats_from_datafile(self, timeout: int = 300):
        """从数据文件刷新统计信息到Redis（后台耗时操作）"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"统计刷新超时（{timeout}秒）")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            stats = {
                'total_items': 0,
                'categories': {},
                'date_range': {
                    'earliest': None,
                    'latest': None
                },
                'file_count': 0,
                'file_types': {},
            }
            
            if self.data_file.exists():
                try:
                    total = 0
                    categories = {}
                    dates = []
                    
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            total += 1
                            try:
                                data = json.loads(line)
                                category = data.get('类别', '未知')
                                categories[category] = categories.get(category, 0) + 1
                                publish_date = data.get('发布日期')
                                if publish_date:
                                    dates.append(publish_date)
                            except (json.JSONDecodeError, KeyError):
                                pass

                    stats['total_items'] = total
                    stats['categories'] = categories
                    if dates:
                        stats['date_range']['earliest'] = min(dates)
                        stats['date_range']['latest'] = max(dates)
                except Exception as e:
                    print(f"[Stats] 读取数据文件失败: {e}")
            
            try:
                if self.files_dir.exists():
                    stats['file_count'] = count_files_recursive(self.files_dir)
                    stats['file_types'] = count_file_types(self.files_dir)
            except Exception as e:
                print(f"[Stats] 统计文件数量失败: {e}")
            
            rm = self._get_redis_manager()
            crawled_count = rm.get_details_crawled()
            stats['crawled_count'] = crawled_count
            stats['visited_urls'] = rm.get_visited_count()
            
            rm.set_stats(stats)
            print(f"[Stats] {self.get_type()} 统计信息已更新: total_items={stats['total_items']}, file_count={stats['file_count']}")
            
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class WJWSpiderAdapter(SpiderAdapter):
    """卫生健康委爬虫适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.script_path = base_dir / 'backend' / 'spiders' / 'crawlers' / 'wjw' / 'start.py'
        self.data_file = base_dir / 'data' / 'wjw' / 'wjw_data.json'
        self.files_dir = base_dir / 'data' / 'wjw' / 'wjw_files'
        self._monitor_thread = None
        self._stop_monitoring = False

    def get_name(self) -> str:
        return '卫生健康委爬虫'

    def get_type(self) -> str:
        return 'wjw'

    def _start_monitor_thread(self):
        """启动状态监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_monitoring = False
        self._monitor_thread = threading.Thread(target=self._monitor_status, daemon=True)
        self._monitor_thread.start()

    def _read_output(self):
        """读取并打印爬虫输出"""
        if self.process and self.process.stdout:
            for line in iter(self.process.stdout.readline, ''):
                if self._stop_monitoring:
                    break
                if line:
                    print(f'[Crawler] {line.rstrip()}')

    def _monitor_status(self):
        """监控爬虫状态"""
        output_thread = threading.Thread(target=self._read_output, daemon=True)
        output_thread.start()

        while not self._stop_monitoring:
            try:
                if self.process and self.process.poll() is None:
                    poll_result = self.process.poll()
                    if poll_result is None:
                        self._get_redis_manager().set_status('running', {
                            'pid': self.process.pid,
                            'monitoring': 'true'
                        })
                else:
                    break
            except Exception:
                pass
            time.sleep(2)

        self._stop_monitoring = True

    def _stop_monitor_thread(self):
        """停止监控线程"""
        self._stop_monitoring = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def start(self, **kwargs) -> bool:
        if self.process and self.process.poll() is None:
            return False

        try:
            rm = self._get_redis_manager()
            rm.set_status('starting', {'started_at': datetime.now().isoformat()})

            cmd = [sys.executable, str(self.script_path)]
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            cwd = str(Path(__file__).resolve().parent.parent.parent)

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.status = 'running'
            self._start_monitor_thread()

            rm.set_status('running', {
                'pid': self.process.pid,
                'started_at': datetime.now().isoformat()
            })

            return True

        except Exception as e:
            self.status = 'error'
            self._get_redis_manager().set_status('error', {'error': str(e)})
            return False

    def stop(self) -> bool:
        rm = self._get_redis_manager()
        rm.set_status('stopping', {'stopped_at': datetime.now().isoformat()})

        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                for _ in range(10):
                    if self.process.poll() is not None:
                        break
                    time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self._stop_monitor_thread()
        self.process = None
        self.status = 'idle'

        rm.set_status('stopped', {
            'stopped_at': datetime.now().isoformat()
        })

        return True

    def pause(self) -> bool:
        if not self.process or self.process.poll() is not None:
            return False

        try:
            self.process.suspend()
            self.status = 'paused'
            self._get_redis_manager().set_paused(True)
            return True
        except Exception:
            return False

    def resume(self) -> bool:
        if not self.process or self.process.poll() is not None:
            return False

        try:
            self.process.resume()
            self.status = 'running'
            self._get_redis_manager().set_paused(False)
            return True
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        rm = self._get_redis_manager()
        redis_status = rm.get_status()
        last_update = redis_status.get('updated_at')

        if not self.process:
            return {
                'status': 'idle',
                'running': False,
                'pid': None,
                'redis_status': redis_status.get('status'),
                'error_count': rm.get_error_count(),
                'links_collected': rm.get_visited_count(),
                'details_crawled': rm.get_crawled_count(),
                'pending_links': rm.get_links_queue_size(),
                'version': redis_status.get('version'),
                'reason': redis_status.get('reason'),
                'last_update': last_update
            }

        poll_result = self.process.poll()
        if poll_result is None:
            return {
                'status': self.status,
                'running': redis_status.get('status') == 'running',
                'pid': self.process.pid,
                'redis_status': redis_status.get('status'),
                'error_count': rm.get_error_count(),
                'links_collected': rm.get_visited_count(),
                'details_crawled': rm.get_crawled_count(),
                'pending_links': rm.get_links_queue_size(),
                'version': redis_status.get('version'),
                'reason': redis_status.get('reason'),
                'last_update': last_update
            }
        else:
            return {
                'status': 'idle',
                'running': False,
                'pid': None,
                'exit_code': poll_result,
                'redis_status': redis_status.get('status'),
                'error_count': rm.get_error_count(),
                'links_collected': rm.get_visited_count(),
                'details_crawled': rm.get_crawled_count(),
                'pending_links': rm.get_links_queue_size(),
                'version': redis_status.get('version'),
                'reason': redis_status.get('reason'),
                'last_update': last_update
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（优先从Redis读取，后台定时刷新）"""
        rm = self._get_redis_manager()
        
        stats = rm.get_stats()
        if stats and stats.get('total_items', 0) > 0:
            return stats
        
        stats = {
            'total_items': 0,
            'categories': {},
            'date_range': {
                'earliest': None,
                'latest': None
            },
            'file_count': 0,
            'file_types': {},
            'last_update': None
        }

        if self.data_file.exists():
            try:
                total = 0
                categories = {}
                dates = []
                
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        total += 1
                        try:
                            data = json.loads(line)
                            category = data.get('类别', '未知')
                            categories[category] = categories.get(category, 0) + 1
                            publish_date = data.get('发布日期')
                            if publish_date:
                                dates.append(publish_date)
                        except (json.JSONDecodeError, KeyError):
                            pass

                stats['total_items'] = total
                stats['categories'] = categories
                if dates:
                    stats['date_range']['earliest'] = min(dates)
                    stats['date_range']['latest'] = max(dates)
                
                stats['last_update'] = datetime.fromtimestamp(
                    self.data_file.stat().st_mtime
                ).isoformat()
            except Exception:
                pass

        try:
            if self.files_dir.exists():
                stats['file_count'] = count_files_recursive(self.files_dir)
                stats['file_types'] = count_file_types(self.files_dir)
        except Exception:
            pass

        crawled_count = rm.get_crawled_count()
        stats['crawled_count'] = crawled_count
        stats['visited_urls'] = rm.get_visited_count()

        rm.set_stats(stats)
        
        return stats

    def _refresh_stats_from_datafile(self, timeout: int = 300):
        """从数据文件刷新统计信息到Redis（后台耗时操作）"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"统计刷新超时（{timeout}秒）")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            stats = {
                'total_items': 0,
                'categories': {},
                'date_range': {
                    'earliest': None,
                    'latest': None
                },
                'file_count': 0,
                'file_types': {},
            }
            
            if self.data_file.exists():
                try:
                    total = 0
                    categories = {}
                    dates = []
                    
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            total += 1
                            try:
                                data = json.loads(line)
                                category = data.get('类别', '未知')
                                categories[category] = categories.get(category, 0) + 1
                                publish_date = data.get('发布日期')
                                if publish_date:
                                    dates.append(publish_date)
                            except (json.JSONDecodeError, KeyError):
                                pass

                    stats['total_items'] = total
                    stats['categories'] = categories
                    if dates:
                        stats['date_range']['earliest'] = min(dates)
                        stats['date_range']['latest'] = max(dates)
                except Exception as e:
                    print(f"[Stats] 读取数据文件失败: {e}")
            
            try:
                if self.files_dir.exists():
                    stats['file_count'] = count_files_recursive(self.files_dir)
                    stats['file_types'] = count_file_types(self.files_dir)
            except Exception as e:
                print(f"[Stats] 统计文件数量失败: {e}")
            
            rm = self._get_redis_manager()
            crawled_count = rm.get_crawled_count()
            stats['crawled_count'] = crawled_count
            stats['visited_urls'] = rm.get_visited_count()
            
            rm.set_stats(stats)
            print(f"[Stats] {self.get_type()} 统计信息已更新: total_items={stats['total_items']}, file_count={stats['file_count']}")
            
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class FLKGovSpiderAdapter(SpiderAdapter):
    """国家法律法规数据库爬虫适配器"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.script_path = base_dir / 'backend' / 'spiders' / 'crawlers' / 'flkgov' / 'start.py'
        self.data_file = base_dir / 'data' / 'flkgov' / 'flkgov_data.json'
        self.files_dir = base_dir / 'data' / 'flkgov' / 'flkgov_files'
        self._monitor_thread = None
        self._stop_monitoring = False

    def get_name(self) -> str:
        return '国家法律法规数据库爬虫'

    def get_type(self) -> str:
        return 'flkgov'

    def _start_monitor_thread(self):
        """启动状态监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_monitoring = False
        self._monitor_thread = threading.Thread(target=self._monitor_status, daemon=True)
        self._monitor_thread.start()

    def _read_output(self):
        """读取并打印爬虫输出"""
        if self.process and self.process.stdout:
            for line in iter(self.process.stdout.readline, ''):
                if self._stop_monitoring:
                    break
                if line:
                    print(f'[Crawler] {line.rstrip()}')

    def _monitor_status(self):
        """监控爬虫状态"""
        output_thread = threading.Thread(target=self._read_output, daemon=True)
        output_thread.start()

        while not self._stop_monitoring:
            try:
                if self.process and self.process.poll() is None:
                    poll_result = self.process.poll()
                    if poll_result is None:
                        self._get_redis_manager().set_status('running', {
                            'pid': self.process.pid,
                            'monitoring': 'true'
                        })
                else:
                    break
            except Exception:
                pass
            time.sleep(2)

        self._stop_monitoring = True

    def _stop_monitor_thread(self):
        """停止监控线程"""
        self._stop_monitoring = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def start(self, **kwargs) -> bool:
        if self.process and self.process.poll() is None:
            return False

        try:
            rm = self._get_redis_manager()
            rm.set_status('starting', {'started_at': datetime.now().isoformat()})

            cmd = [sys.executable, str(self.script_path)]
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            cwd = str(Path(__file__).resolve().parent.parent.parent)

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=cwd,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

            self.status = 'running'
            self._start_monitor_thread()

            rm.set_status('running', {
                'pid': self.process.pid,
                'started_at': datetime.now().isoformat()
            })

            return True

        except Exception as e:
            self.status = 'error'
            self._get_redis_manager().set_status('error', {'error': str(e)})
            return False

    def stop(self) -> bool:
        rm = self._get_redis_manager()
        rm.set_status('stopping', {'stopped_at': datetime.now().isoformat()})

        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                for _ in range(10):
                    if self.process.poll() is not None:
                        break
                    time.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        self._stop_monitor_thread()
        self.process = None
        self.status = 'idle'

        rm.set_status('stopped', {
            'stopped_at': datetime.now().isoformat()
        })

        return True

    def pause(self) -> bool:
        if not self.process or self.process.poll() is not None:
            return False

        try:
            self.process.suspend()
            self.status = 'paused'
            self._get_redis_manager().set_paused(True)
            return True
        except Exception:
            return False

    def resume(self) -> bool:
        if not self.process or self.process.poll() is not None:
            return False

        try:
            self.process.resume()
            self.status = 'running'
            self._get_redis_manager().set_paused(False)
            return True
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        rm = self._get_redis_manager()
        redis_status = rm.get_status()
        last_update = redis_status.get('updated_at')

        if not self.process:
            return {
                'status': 'idle',
                'running': False,
                'pid': None,
                'redis_status': redis_status.get('status'),
                'error_count': rm.get_error_count(),
                'links_collected': rm.get_visited_count(),
                'details_crawled': rm.get_crawled_count(),
                'pending_links': rm.get_links_queue_size(),
                'version': redis_status.get('version'),
                'reason': redis_status.get('reason'),
                'last_update': last_update
            }

        poll_result = self.process.poll()
        if poll_result is None:
            return {
                'status': self.status,
                'running': redis_status.get('status') == 'running',
                'pid': self.process.pid,
                'redis_status': redis_status.get('status'),
                'error_count': rm.get_error_count(),
                'links_collected': rm.get_visited_count(),
                'details_crawled': rm.get_crawled_count(),
                'pending_links': rm.get_links_queue_size(),
                'version': redis_status.get('version'),
                'reason': redis_status.get('reason'),
                'last_update': last_update
            }
        else:
            return {
                'status': 'idle',
                'running': False,
                'pid': None,
                'exit_code': poll_result,
                'redis_status': redis_status.get('status'),
                'error_count': rm.get_error_count(),
                'links_collected': rm.get_visited_count(),
                'details_crawled': rm.get_crawled_count(),
                'pending_links': rm.get_links_queue_size(),
                'version': redis_status.get('version'),
                'reason': redis_status.get('reason'),
                'last_update': last_update
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（优先从Redis读取，后台定时刷新）"""
        rm = self._get_redis_manager()
        
        stats = rm.get_stats()
        if stats and stats.get('total_items', 0) > 0:
            return stats
        
        stats = {
            'total_items': 0,
            'categories': {},
            'date_range': {
                'earliest': None,
                'latest': None
            },
            'file_count': 0,
            'file_types': {},
            'last_update': None
        }

        if self.data_file.exists():
            try:
                total = 0
                categories = {}
                dates = []
                
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        total += 1
                        try:
                            data = json.loads(line)
                            category = data.get('类别', '未知')
                            categories[category] = categories.get(category, 0) + 1
                            publish_date = data.get('颁布日期')
                            if publish_date:
                                dates.append(publish_date)
                        except (json.JSONDecodeError, KeyError):
                            pass

                stats['total_items'] = total
                stats['categories'] = categories
                if dates:
                    stats['date_range']['earliest'] = min(dates)
                    stats['date_range']['latest'] = max(dates)
                
                stats['last_update'] = datetime.fromtimestamp(
                    self.data_file.stat().st_mtime
                ).isoformat()
            except Exception:
                pass

        try:
            if self.files_dir.exists():
                stats['file_count'] = count_files_recursive(self.files_dir)
                stats['file_types'] = count_file_types(self.files_dir)
        except Exception:
            pass

        crawled_count = rm.get_crawled_count()
        stats['crawled_count'] = crawled_count
        stats['visited_urls'] = rm.get_visited_count()

        rm.set_stats(stats)
        
        return stats

    def _refresh_stats_from_datafile(self, timeout: int = 300):
        """从数据文件刷新统计信息到Redis（后台耗时操作）"""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"统计刷新超时（{timeout}秒）")
        
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            stats = {
                'total_items': 0,
                'categories': {},
                'date_range': {
                    'earliest': None,
                    'latest': None
                },
                'file_count': 0,
                'file_types': {},
            }
            
            if self.data_file.exists():
                try:
                    total = 0
                    categories = {}
                    dates = []
                    
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            total += 1
                            try:
                                data = json.loads(line)
                                category = data.get('类别', '未知')
                                categories[category] = categories.get(category, 0) + 1
                                publish_date = data.get('颁布日期')
                                if publish_date:
                                    dates.append(publish_date)
                            except (json.JSONDecodeError, KeyError):
                                pass

                    stats['total_items'] = total
                    stats['categories'] = categories
                    if dates:
                        stats['date_range']['earliest'] = min(dates)
                        stats['date_range']['latest'] = max(dates)
                except Exception as e:
                    print(f"[Stats] 读取数据文件失败: {e}")
            
            try:
                if self.files_dir.exists():
                    stats['file_count'] = count_files_recursive(self.files_dir)
                    stats['file_types'] = count_file_types(self.files_dir)
            except Exception as e:
                print(f"[Stats] 统计文件数量失败: {e}")
            
            rm = self._get_redis_manager()
            crawled_count = rm.get_crawled_count()
            stats['crawled_count'] = crawled_count
            stats['visited_urls'] = rm.get_visited_count()
            
            rm.set_stats(stats)
            print(f"[Stats] {self.get_type()} 统计信息已更新: total_items={stats['total_items']}, file_count={stats['file_count']}")
            
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class SpiderManager:
    """爬虫管理器"""

    _adapters: Dict[str, SpiderAdapter] = {}
    _refresh_lock = threading.Lock()
    _refreshing = set()

    @classmethod
    def register(cls, spider_type: str, adapter: SpiderAdapter):
        cls._adapters[spider_type] = adapter

    @classmethod
    def get_adapter(cls, spider_type: str) -> Optional[SpiderAdapter]:
        return cls._adapters.get(spider_type)

    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        result = {}
        for spider_type, adapter in cls._adapters.items():
            status = adapter.get_status()
            stats = adapter.get_stats()
            last_update = status.get('last_update') or stats.get('last_update')
            result[spider_type] = {**status, **stats, 'last_update': last_update}
        return result

    @classmethod
    def start_spider(cls, spider_type: str, **kwargs) -> bool:
        adapter = cls.get_adapter(spider_type)
        if adapter:
            return adapter.start(**kwargs)
        return False

    @classmethod
    def stop_spider(cls, spider_type: str) -> bool:
        adapter = cls.get_adapter(spider_type)
        if adapter:
            return adapter.stop()
        return False

    @classmethod
    def get_spider_stats(cls, spider_type: str) -> Dict[str, Any]:
        adapter = cls.get_adapter(spider_type)
        if adapter:
            return adapter.get_stats()
        return {}

    @classmethod
    def refresh_all_stats_background(cls, timeout: int = 300):
        """后台刷新所有爬虫的统计信息（耗时操作，使用线程避免阻塞API）"""
        def do_refresh():
            with cls._refresh_lock:
                for spider_type, adapter in cls._adapters.items():
                    if spider_type in cls._refreshing:
                        continue
                    cls._refreshing.add(spider_type)
                    try:
                        print(f"[Stats] 开始后台刷新 {spider_type} 统计信息...")
                        adapter._refresh_stats_from_datafile(timeout=timeout)
                        print(f"[Stats] {spider_type} 统计信息刷新完成")
                    except Exception as e:
                        print(f"[Stats] {spider_type} 统计信息刷新失败: {e}")
                    finally:
                        cls._refreshing.discard(spider_type)
        
        thread = threading.Thread(target=do_refresh, daemon=True)
        thread.start()
        return True


SpiderManager.register('nhsa', NHSASpiderAdapter())
SpiderManager.register('wjw', WJWSpiderAdapter())
SpiderManager.register('flkgov', FLKGovSpiderAdapter())
