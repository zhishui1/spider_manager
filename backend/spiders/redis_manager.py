"""
Redis管理器 - 统一管理爬虫相关的Redis操作
优化键设计，减少键数量，将相关数据合并到一张表中
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import redis


class RedisManager:
    """Redis管理器单例"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._client = None
        self._connect()

    def _connect(self):
        """建立Redis连接"""
        try:
            self._client = redis.Redis(
                host='192.168.1.40',
                password='1421nbnb',
                port=6379,
                db=0,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self._client.ping()
            print("[Redis] 连接成功")
        except redis.ConnectionError as e:
            print(f"[Redis] 连接失败: {e}")
            self._client = None
        except Exception as e:
            print(f"[Redis] 未知错误: {e}")
            self._client = None

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def get_client(self) -> Optional[redis.Redis]:
        """获取Redis客户端"""
        return self._client


class SpiderRedisManager:
    """爬虫专用Redis管理器 - 优化键设计，减少键数量"""

    def __init__(self, spider_type: str):
        self.spider_type = spider_type
        self.rm = RedisManager()
        self._prefix = f'spider:{spider_type}'
        self._state_key = f'{self._prefix}:state'
        self._progress_key = f'{self._prefix}:progress'
        self._pagination_key = f'{self._prefix}:pagination'

    @property
    def client(self) -> Optional[redis.Redis]:
        """获取Redis客户端"""
        return self.rm.get_client()

    def _key(self, key: str) -> str:
        """生成带前缀的键名"""
        return f'{self._prefix}:{key}'

    # ============ 状态管理（合并到state表） ============

    def set_status(self, status: str, details: Dict[str, Any] = None) -> bool:
        """设置爬虫状态"""
        try:
            if not self.client:
                return False
            state = {'status': status, 'updated_at': datetime.now().isoformat()}
            if details:
                state.update(details)
            self.client.hset(self._state_key, mapping=state)
            self._increment_status_version()
            return True
        except Exception as e:
            print(f"[Redis] 设置状态失败: {e}")
            return False

    def _get_status_version(self) -> int:
        """获取状态版本号"""
        try:
            if not self.client:
                return 0
            version = self.client.get(self._key('status_version'))
            return int(version) if version else 0
        except Exception:
            return 0

    def _increment_status_version(self) -> bool:
        """递增状态版本号"""
        try:
            if not self.client:
                return False
            self.client.incr(self._key('status_version'))
            return True
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        """获取爬虫状态"""
        try:
            if not self.client:
                return {'status': 'unknown', 'error': 'Redis未连接'}
            state = self.client.hgetall(self._state_key) or {}
            return {
                'status': state.get('status', 'idle'),
                'links_collected': self.get_visited_count(),
                'pending_links': self.get_links_queue_size(),
                'details_crawled': self.get_details_crawled(),
                'updated_at': state.get('updated_at'),
                'reason': state.get('reason'),
                'version': self._get_status_version(),
                'source': 'redis'
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

    def is_running(self) -> bool:
        """检查爬虫是否在运行"""
        status = self.get_status()
        return status.get('status') in ['running', 'starting']

    def is_paused(self) -> bool:
        """检查爬虫是否暂停"""
        try:
            if not self.client:
                return False
            return self.client.hget(self._state_key, 'paused') == '1'
        except Exception:
            return False

    def set_paused(self, paused: bool) -> bool:
        """设置暂停状态"""
        try:
            if not self.client:
                return False
            if paused:
                self.client.hset(self._state_key, 'paused', '1')
            else:
                self.client.hdel(self._state_key, 'paused')
            return True
        except Exception as e:
            print(f"[Redis] 设置暂停状态失败: {e}")
            return False

    # ============ 进度管理（合并到progress表） ============

    def update_progress(self, crawled: int, total: int, current_category: str = '',
                       errors: int = 0) -> bool:
        """更新爬取进度"""
        try:
            if not self.client:
                return False
            self.client.hset(self._progress_key, mapping={
                'crawled': str(crawled),
                'total': str(total),
                'current_category': current_category,
                'errors': str(errors),
                'updated_at': datetime.now().isoformat()
            })
            return True
        except Exception as e:
            print(f"[Redis] 更新进度失败: {e}")
            return False

    def get_progress(self) -> Dict[str, str]:
        """获取爬取进度"""
        try:
            if not self.client:
                return {}
            return self.client.hgetall(self._progress_key) or {}
        except Exception:
            return {}

    # ============ 统计管理（合并到state表） ============

    def increment_details_crawled(self, count: int = 1) -> int:
        """增加已爬取详情数量"""
        try:
            if not self.client:
                return 0
            return self.client.hincrby(self._state_key, 'details_crawled', count)
        except Exception:
            return 0

    def get_details_crawled(self) -> int:
        """获取已爬取详情数量"""
        try:
            if not self.client:
                return 0
            value = self.client.hget(self._state_key, 'details_crawled')
            return int(value) if value else 0
        except Exception:
            return 0

    def set_details_crawled(self, count: int) -> bool:
        """设置已爬取详情数量"""
        try:
            if not self.client:
                return False
            self.client.hset(self._state_key, 'details_crawled', str(count))
            return True
        except Exception:
            return False

    def increment_error_count(self, count: int = 1) -> int:
        """增加错误计数"""
        try:
            if not self.client:
                return 0
            return self.client.hincrby(self._state_key, 'error_count', count)
        except Exception:
            return 0

    def get_error_count(self) -> int:
        """获取错误数量"""
        try:
            if not self.client:
                return 0
            value = self.client.hget(self._state_key, 'error_count')
            return int(value) if value else 0
        except Exception:
            return 0

    # ============ 统计信息管理（独立stats表，用于快速读取） ============

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（从Redis读取）"""
        try:
            if not self.client:
                return {}
            stats_key = self._key('stats')
            stats = self.client.hgetall(stats_key) or {}
            
            result = {
                'total_items': int(stats.get('total_items', 0)),
                'file_count': int(stats.get('file_count', 0)),
                'html_count': int(stats.get('html_count', 0)),
                'crawled_count': int(stats.get('crawled_count', 0)),
                'visited_urls': int(stats.get('visited_urls', 0)),
                'last_update': stats.get('last_update'),
            }
            
            categories_json = stats.get('categories')
            if categories_json:
                result['categories'] = json.loads(categories_json)
            else:
                result['categories'] = {}
            
            date_earliest = stats.get('date_earliest')
            date_latest = stats.get('date_latest')
            if date_earliest or date_latest:
                result['date_range'] = {
                    'earliest': date_earliest,
                    'latest': date_latest
                }
            else:
                result['date_range'] = {'earliest': None, 'latest': None}
            
            file_types_json = stats.get('file_types')
            if file_types_json:
                result['file_types'] = json.loads(file_types_json)
            else:
                result['file_types'] = {}
            
            return result
        except Exception as e:
            print(f"[Redis] 获取统计信息失败: {e}")
            return {}

    def set_stats(self, stats: Dict[str, Any]) -> bool:
        """设置统计信息（覆盖更新）"""
        try:
            if not self.client:
                return False
            stats_key = self._key('stats')
            
            data = {
                'total_items': str(stats.get('total_items', 0)),
                'file_count': str(stats.get('file_count', 0)),
                'html_count': str(stats.get('html_count', 0)),
                'crawled_count': str(stats.get('crawled_count', 0)),
                'visited_urls': str(stats.get('visited_urls', 0)),
                'last_update': datetime.now().isoformat(),
            }
            
            if stats.get('categories'):
                data['categories'] = json.dumps(stats['categories'], ensure_ascii=False)
            
            if stats.get('date_range'):
                if stats['date_range'].get('earliest'):
                    data['date_earliest'] = stats['date_range']['earliest']
                if stats['date_range'].get('latest'):
                    data['date_latest'] = stats['date_range']['latest']
            
            if stats.get('file_types'):
                data['file_types'] = json.dumps(stats['file_types'], ensure_ascii=False)
            
            self.client.hset(stats_key, mapping=data)
            return True
        except Exception as e:
            print(f"[Redis] 设置统计信息失败: {e}")
            return False

    def update_stats_incremental(self, item_data: Dict[str, Any] = None, 
                                  file_count_delta: int = 0,
                                  crawled_delta: int = 0) -> bool:
        """增量更新统计信息（新增item或文件时调用）"""
        try:
            if not self.client:
                return False
            stats_key = self._key('stats')
            
            current = self.client.hgetall(stats_key) or {}
            
            if item_data:
                total = int(current.get('total_items', 0)) + 1
                self.client.hset(stats_key, 'total_items', str(total))
                
                category = item_data.get('类别', '未知')
                categories_json = current.get('categories', '{}')
                categories = json.loads(categories_json)
                categories[category] = categories.get(category, 0) + 1
                self.client.hset(stats_key, 'categories', json.dumps(categories, ensure_ascii=False))
                
                publish_date = item_data.get('发布日期') or item_data.get('颁布日期')
                if publish_date:
                    date_earliest = current.get('date_earliest')
                    date_latest = current.get('date_latest')
                    if not date_earliest or publish_date < date_earliest:
                        self.client.hset(stats_key, 'date_earliest', publish_date)
                    if not date_latest or publish_date > date_latest:
                        self.client.hset(stats_key, 'date_latest', publish_date)
            
            if file_count_delta != 0:
                current_count = int(current.get('file_count', 0))
                new_count = current_count + file_count_delta
                self.client.hset(stats_key, 'file_count', str(max(0, new_count)))
            
            if crawled_delta != 0:
                current_crawled = int(current.get('crawled_count', 0))
                new_crawled = current_crawled + crawled_delta
                self.client.hset(stats_key, 'crawled_count', str(max(0, new_crawled)))
            
            self.client.hset(stats_key, 'last_update', datetime.now().isoformat())
            return True
        except Exception as e:
            print(f"[Redis] 增量更新统计信息失败: {e}")
            return False

    def increment_file_count(self, delta: int = 1) -> int:
        """增加文件计数"""
        try:
            if not self.client:
                return 0
            stats_key = self._key('stats')
            return self.client.hincrby(stats_key, 'file_count', delta)
        except Exception:
            return 0

    def increment_crawled_count(self, delta: int = 1) -> int:
        """增加已爬取计数"""
        try:
            if not self.client:
                return 0
            stats_key = self._key('stats')
            return self.client.hincrby(stats_key, 'crawled_count', delta)
        except Exception:
            return 0

    # ============ URL去重 ============

    def is_url_visited(self, url: str) -> bool:
        """检查URL是否已访问（去重）"""
        try:
            if not self.client:
                return False
            return self.client.sismember(self._key('visited_urls'), url)
        except Exception:
            return False

    def mark_url_visited(self, url: str) -> bool:
        """标记URL为已访问"""
        try:
            if not self.client:
                return False
            self.client.sadd(self._key('visited_urls'), url)
            return True
        except Exception as e:
            print(f"[Redis] 标记URL失败: {e}")
            return False

    def check_and_mark_url(self, url: str) -> bool:
        """检查并标记URL，返回是否新URL"""
        if self.is_url_visited(url):
            return False
        self.mark_url_visited(url)
        return True

    def is_duplicate(self, url: str) -> bool:
        """检查URL是否重复（用于URL去重）"""
        return self.is_url_visited(url)

    def get_visited_count(self) -> int:
        """获取已访问URL数量"""
        try:
            if not self.client:
                return 0
            return self.client.scard(self._key('visited_urls'))
        except Exception:
            return 0

    def mark_url_crawled(self, url: str) -> bool:
        """标记详情页URL已爬取（去重）"""
        try:
            if not self.client:
                return False
            self.client.sadd(self._key('crawled_urls'), url)
            return True
        except Exception as e:
            print(f"[Redis] 标记URL已爬取失败: {e}")
            return False

    def mark_url_empty_content(self, url: str) -> bool:
        """标记URL内容为空（不计入爬取失败，不重试）"""
        try:
            if not self.client:
                return False
            self.client.sadd(self._key('empty_content_urls'), url)
            return True
        except Exception as e:
            print(f"[Redis] 标记空内容URL失败: {e}")
            return False

    def is_url_crawled(self, url: str) -> bool:
        """检查URL是否已爬取详情"""
        try:
            if not self.client:
                return False
            return self.client.sismember(self._key('crawled_urls'), url)
        except Exception:
            return False

    def get_crawled_count(self) -> int:
        """获取已爬取详情页数量"""
        try:
            if not self.client:
                return 0
            return self.client.scard(self._key('crawled_urls'))
        except Exception:
            return 0

    # ============ URL队列管理 ============

    def push_to_queue(self, url: str, priority: float = 0.0) -> bool:
        """添加URL到队列（有序集合）"""
        try:
            if not self.client:
                return False
            self.client.zadd(self._key('url_queue'), {url: priority})
            return True
        except Exception as e:
            print(f"[Redis] 添加到队列失败: {e}")
            return False

    def pop_from_queue(self) -> Optional[str]:
        """从队列取出URL（优先级最低的）"""
        try:
            if not self.client:
                return None
            result = self.client.zpopmin(self._key('url_queue'))
            if result:
                return result[0][0]
            return None
        except Exception as e:
            print(f"[Redis] 从队列取出失败: {e}")
            return None

    def get_queue_size(self) -> int:
        """获取队列大小"""
        try:
            if not self.client:
                return 0
            return self.client.zcard(self._key('url_queue'))
        except Exception:
            return 0

    # ============ 错误管理 ============

    def log_error(self, error_type: str, url: str, message: str) -> bool:
        """记录错误"""
        try:
            if not self.client:
                return False
            error_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': error_type,
                'url': url,
                'message': message
            }
            self.client.lpush(self._key('errors'), json.dumps(error_entry, ensure_ascii=False))
            self.client.ltrim(self._key('errors'), 0, 99)
            self.increment_error_count(1)
            return True
        except Exception as e:
            print(f"[Redis] 记录错误失败: {e}")
            return False

    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """获取最近错误"""
        try:
            if not self.client:
                return []
            errors = self.client.lrange(self._key('errors'), 0, limit - 1)
            return [json.loads(e) for e in errors]
        except Exception:
            return []

    # ============ 链接队列管理（两阶段爬取） ============

    def push_to_links_queue(self, link_data: Dict[str, Any]) -> bool:
        """添加详情页链接到队列"""
        try:
            if not self.client:
                return False
            self.client.lpush(self._key('links_queue'), json.dumps(link_data, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"[Redis] 添加到链接队列失败: {e}")
            return False

    def pop_from_links_queue(self) -> Optional[Dict[str, Any]]:
        """从详情页队列取出链接（FIFO）"""
        try:
            if not self.client:
                return None
            data = self.client.rpop(self._key('links_queue'))
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[Redis] 从链接队列取出失败: {e}")
            return None

    def get_links_queue_size(self) -> int:
        """获取待爬取详情链接队列大小"""
        try:
            if not self.client:
                return 0
            return self.client.llen(self._key('links_queue'))
        except Exception:
            return 0

    def has_pending_links(self) -> bool:
        """检查是否有待爬取的详情链接"""
        return self.get_links_queue_size() > 0

    # ============ 翻页进度管理（合并到pagination表） ============

    def set_last_pagination_page(self, column_id: int, page: int) -> bool:
        """记录翻页进度"""
        try:
            if not self.client:
                return False
            self.client.hset(self._pagination_key, str(column_id), str(page))
            return True
        except Exception as e:
            print(f"[Redis] 记录翻页进度失败: {e}")
            return False

    def get_last_pagination_page(self, column_id: int) -> int:
        """获取指定栏目的翻页进度"""
        try:
            if not self.client:
                return 0
            page = self.client.hget(self._pagination_key, str(column_id))
            return int(page) if page else 0
        except Exception:
            return 0

    def set_pagination_complete(self, column_id: int, complete: bool) -> bool:
        """标记栏目翻页是否完成"""
        try:
            if not self.client:
                return False
            complete_key = f'{column_id}_complete'
            if complete:
                self.client.hset(self._pagination_key, complete_key, '1')
            else:
                self.client.hdel(self._pagination_key, complete_key)
            return True
        except Exception as e:
            print(f"[Redis] 设置翻页完成状态失败: {e}")
            return False

    def is_pagination_complete(self, column_id: int) -> bool:
        """检查栏目翻页是否完成"""
        try:
            if not self.client:
                return False
            complete_key = f'{column_id}_complete'
            return self.client.hget(self._pagination_key, complete_key) == '1'
        except Exception:
            return False

    def get_all_pagination_progress(self) -> Dict[str, str]:
        """获取所有栏目的翻页进度"""
        try:
            if not self.client:
                return {}
            return self.client.hgetall(self._pagination_key) or {}
        except Exception:
            return {}

    def has_incomplete_pagination(self, column_configs: Dict[int, Dict]) -> bool:
        """检查是否有未完成的翻页"""
        for column_id, config in column_configs.items():
            if not self.is_pagination_complete(column_id):
                return True
        return False

    # ============ 检查点管理 ============

    def save_checkpoint(self, checkpoint_data: Dict[str, Any]) -> bool:
        """保存检查点数据"""
        try:
            if not self.client:
                return False
            checkpoint_data['saved_at'] = datetime.now().isoformat()
            self.client.set(self._key('checkpoint'), json.dumps(checkpoint_data, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"[Redis] 保存检查点失败: {e}")
            return False

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """加载检查点数据"""
        try:
            if not self.client:
                return None
            data = self.client.get(self._key('checkpoint'))
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[Redis] 加载检查点失败: {e}")
            return None

    # ============ 清理 ============

    def cleanup(self) -> bool:
        """清理该爬虫的所有Redis数据（完全重置）"""
        try:
            if not self.client:
                return False
            keys_to_delete = [
                self._state_key,
                self._progress_key,
                self._pagination_key,
                self._key('visited_urls'),
                self._key('url_queue'),
                self._key('errors'),
                self._key('links_queue'),
                self._key('crawled_urls'),
                self._key('checkpoint'),
            ]
            self.client.delete(*keys_to_delete)
            return True
        except Exception as e:
            print(f"[Redis] 清理失败: {e}")
            return False

    def reset_state(self) -> bool:
        """只清理状态数据，保留进度和去重数据（用于断点续传）"""
        try:
            if not self.client:
                return False
            keys_to_delete = [
                self._state_key,
                self._progress_key,
                self._key('url_queue'),
                self._key('errors'),
                self._key('checkpoint'),
            ]
            self.client.delete(*keys_to_delete)
            return True
        except Exception as e:
            print(f"[Redis] 重置状态失败: {e}")
            return False


def get_spider_redis_manager(spider_type: str) -> SpiderRedisManager:
    """获取指定爬虫的Redis管理器"""
    return SpiderRedisManager(spider_type)


def get_all_spider_status() -> Dict[str, Dict[str, Any]]:
    """获取所有爬虫状态"""
    result = {}
    spider_types = ['nhsa', 'wjw']
    for spider_type in spider_types:
        rm = get_spider_redis_manager(spider_type)
        result[spider_type] = rm.get_status()
    return result
