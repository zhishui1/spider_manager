"""
API views for spider management.
提供爬虫控制、数据查询、日志查看等API接口
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .adapters import SpiderManager, count_files_recursive
from .redis_manager import get_spider_redis_manager
from .file_utils import create_zip_from_directory, create_batch_zip, safe_filename

logger = logging.getLogger(__name__)


def get_spider_config_by_id(spider_id: str) -> dict:
    """
    根据 spider_id 获取爬虫配置
    从注册中心获取配置
    """
    from .crawlers import get_spider_by_id
    config = get_spider_by_id(spider_id)
    if config:
        return config
    return {}


def get_all_spider_configs() -> List[dict]:
    """获取所有爬虫配置"""
    from .crawlers import get_all_spiders
    return get_all_spiders()


def safe_json_response(data: dict, status: int = 200) -> JsonResponse:
    """安全的JSON响应"""
    try:
        return JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': '响应序列化失败',
            'details': str(e)
        }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SpiderStatusView(View):
    """爬虫状态API - 优先从Redis读取，后台定时刷新"""

    def get(self, request):
        spider_type = request.GET.get('type')

        try:
            if spider_type:
                adapter = SpiderManager.get_adapter(spider_type)
                if adapter:
                    status = adapter.get_status()
                    stats = adapter.get_stats()

                    if not stats.get('total_items'):
                        SpiderManager.refresh_all_stats_background(timeout=300)

                    if 'categories' not in stats:
                        stats['categories'] = {}
                    if 'date_range' not in stats:
                        stats['date_range'] = {'earliest': None, 'latest': None}

                    last_update = status.get('last_update') or stats.get('last_update')
                    return safe_json_response({
                        'success': True,
                        'data': {
                            **status,
                            **stats,
                            'last_update': last_update,
                            'spider_name': adapter.get_name(),
                            'spider_type': adapter.get_type()
                        }
                    })

                return safe_json_response({
                    'success': False,
                    'error': 'Spider type not found'
                }, status=404)

            all_status = SpiderManager.get_all_status()
            
            need_refresh = False
            for spider_type, status_data in all_status.items():
                adapter = SpiderManager.get_adapter(spider_type)
                if adapter:
                    stats = adapter.get_stats()
                    if not stats.get('total_items'):
                        need_refresh = True
                        break
            
            if need_refresh:
                SpiderManager.refresh_all_stats_background(timeout=300)

            result = {}
            for spider_type, status_data in all_status.items():
                adapter = SpiderManager.get_adapter(spider_type)
                if adapter:
                    result[spider_type] = {
                        **status_data,
                        'spider_name': adapter.get_name(),
                        'spider_type': spider_type
                    }
                else:
                    result[spider_type] = {
                        **status_data,
                        'spider_name': spider_type,
                        'spider_type': spider_type
                    }

            return safe_json_response({
                'success': True,
                'data': result
            })

        except Exception as e:
            logger.error(f"获取爬虫状态失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '获取状态失败',
                'details': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SpiderControlView(View):
    """爬虫控制API"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            spider_type = data.get('spider_type')

            if not spider_type:
                return safe_json_response({
                    'success': False,
                    'error': 'spider_type is required'
                }, status=400)

            if not action:
                return safe_json_response({
                    'success': False,
                    'error': 'action is required'
                }, status=400)

            if action not in ['start', 'stop']:
                return safe_json_response({
                    'success': False,
                    'error': f'Unknown action: {action}. Only start and stop are supported.'
                }, status=400)

            adapter = SpiderManager.get_adapter(spider_type)
            if not adapter:
                return safe_json_response({
                    'success': False,
                    'error': f'Spider type not found: {spider_type}'
                }, status=404)

            result = False

            if action == 'start':
                result = SpiderManager.start_spider(spider_type)
            elif action == 'stop':
                result = SpiderManager.stop_spider(spider_type)

            if result:
                logger.info(f"爬虫操作成功: {spider_type} - {action}")
                return safe_json_response({
                    'success': True,
                    'message': f'{action.capitalize()} executed successfully',
                    'spider_type': spider_type,
                    'action': action
                })
            else:
                action_name = '启动' if action == 'start' else '停止'
                logger.warning(f"爬虫操作失败: {spider_type} - {action}")
                return safe_json_response({
                    'success': False,
                    'error': f'{action_name}失败',
                    'spider_type': spider_type,
                    'action': action
                }, status=500)

        except json.JSONDecodeError:
            logger.error("Invalid JSON in request body")
            return safe_json_response({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            logger.error(f"爬虫控制异常: {e}")
            return safe_json_response({
                'success': False,
                'error': 'Internal server error',
                'details': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CrawledDataView(View):
    """爬取数据API"""

    def get(self, request):
        try:
            spider_type = request.GET.get('type', 'nhsa')
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            keyword = request.GET.get('keyword')
            date_start = request.GET.get('date_start')
            date_end = request.GET.get('date_end')
            sort_field = request.GET.get('sort_field', 'publish_date')
            sort_order = request.GET.get('sort_order', 'desc')

            base_dir = Path(__file__).resolve().parent.parent.parent
            data_file = base_dir / 'data' / spider_type / f'{spider_type}_data.json'

            if not data_file.exists():
                return safe_json_response({
                    'success': True,
                    'data': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'message': '数据文件不存在'
                })

            items = []
            files_dir = base_dir / 'data' / spider_type / f'{spider_type}_files'
            with open(data_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        raw_data = json.loads(line)
                        item_id = raw_data.get('item_id')
                        data = {
                            'item_id': item_id,
                            'title': raw_data.get('title'),
                            'publish_date': raw_data.get('发布日期') or raw_data.get('publish_date'),
                            'url': raw_data.get('url'),
                            'data': raw_data.get('data', {}),
                        }
                        publish_date = (data.get('publish_date') or '').strip()
                        
                        if date_start or date_end:
                            in_range = True
                            if date_start and publish_date and publish_date < date_start:
                                in_range = False
                            if date_end and publish_date and publish_date > date_end:
                                in_range = False
                            if not in_range:
                                continue
                        if keyword and keyword not in data.get('title', ''):
                            continue
                        
                        if item_id and files_dir.exists():
                            item_dir = files_dir / str(item_id)
                            if item_dir.exists() and item_dir.is_dir():
                                file_count = sum(1 for _ in item_dir.iterdir() if _.is_file())
                                data['file_count'] = file_count
                            else:
                                data['file_count'] = 0
                        else:
                            data['file_count'] = 0
                        
                        data['_line_number'] = line_num
                        items.append(data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"解析JSON行失败 (行号:{line_num}): {e}")
                        continue

            def get_sort_value(item):
                sort_val = item.get(sort_field, item.get(sort_field.lower(), ''))
                if isinstance(sort_val, str):
                    return sort_val
                return str(sort_val)

            reverse = sort_order.lower() == 'desc'
            items.sort(key=get_sort_value, reverse=reverse)

            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_items = items[start:end]

            for item in paginated_items:
                item.pop('_line_number', None)

            return safe_json_response({
                'success': True,
                'data': paginated_items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            })

        except Exception as e:
            logger.error(f"获取爬取数据失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '获取数据失败',
                'details': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CrawledFilesView(View):
    """爬取附件文件API"""

    def get(self, request):
        try:
            spider_type = request.GET.get('type', 'nhsa')
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 20)), 100)
            keyword = request.GET.get('keyword')

            base_dir = Path(__file__).resolve().parent.parent.parent
            files_dir = base_dir / 'data' / spider_type / f'{spider_type}_files'

            if not files_dir.exists():
                return safe_json_response({
                    'success': True,
                    'data': [],
                    'total': 0,
                    'page': page,
                    'page_size': page_size,
                    'message': '文件目录不存在'
                })

            def scan_files(directory: Path) -> list:
                """递归扫描目录下所有文件"""
                items = []
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        file_name = file_path.name
                        if keyword and keyword not in file_name:
                            continue
                        items.append({
                            'name': file_name,
                            'path': str(file_path.relative_to(base_dir)).replace('\\', '/'),
                            'size': file_path.stat().st_size,
                            'size_formatted': self.format_size(file_path.stat().st_size),
                            'extension': file_path.suffix.lower(),
                            'modified_time': file_path.stat().st_mtime,
                            'modified_time_formatted': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
                    elif file_path.is_dir():
                        items.extend(scan_files(file_path))
                return items

            items = scan_files(files_dir)
            items.sort(key=lambda x: x['modified_time'], reverse=True)

            total = len(items)
            start = (page - 1) * page_size
            end = start + page_size
            paginated_items = items[start:end]

            return safe_json_response({
                'success': True,
                'data': paginated_items,
                'total': total,
                'page': page,
                'page_size': page_size
            })

        except Exception as e:
            logger.error(f"获取爬取文件失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '获取文件列表失败',
                'details': str(e)
            }, status=500)

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f}{unit}"
            size /= 1024
        return f"{size:.2f}TB"


@method_decorator(csrf_exempt, name='dispatch')
class FileDownloadView(View):
    """文件下载API"""

    def get(self, request):
        try:
            path_param = request.GET.get('path')
            if not path_param:
                return safe_json_response({
                    'success': False,
                    'error': 'path is required'
                }, status=400)

            base_dir = Path(__file__).resolve().parent.parent.parent

            file_path = Path(path_param)
            if not file_path.is_absolute():
                file_path = base_dir / path_param

            if not file_path.exists() or not file_path.is_file():
                return safe_json_response({
                    'success': False,
                    'error': '文件不存在'
                }, status=404)

            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                    response = HttpResponse(content, content_type='application/octet-stream')
                    filename = file_path.name
                    try:
                        encoded_filename = urllib.parse.quote(filename, safe='')
                        response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"; filename*=utf-8\'\'{encoded_filename}'
                    except Exception:
                        response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
                    return response
            except IOError as e:
                logger.error(f"读取文件失败: {e}")
                return safe_json_response({
                    'success': False,
                    'error': '读取文件失败'
                }, status=500)

        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '下载失败',
                'details': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SpiderLogsView(View):
    """爬虫日志API"""

    def _match_log_type(self, log_entry: Dict, log_type: str) -> bool:
        """判断日志是否匹配指定类型"""
        if not log_type or log_type == 'all':
            return True
        
        msg = log_entry.get('message', '')
        level = log_entry.get('level', '').lower()
        
        if log_type == 'links':
            return any(keyword in msg for keyword in ['翻页', '栏目', '入队', '链接收集'])
        elif log_type == 'details':
            return any(keyword in msg for keyword in ['详情', 'Crawl success', '已爬取'])
        elif log_type == 'download':
            return any(keyword in msg for keyword in ['下载', 'Download'])
        elif log_type == 'error':
            return level == 'error' or any(keyword in msg for keyword in ['错误', '[错误]', '失败'])
        return True

    def get(self, request):
        try:
            spider_type = request.GET.get('type')
            level = request.GET.get('level')
            log_type = request.GET.get('log_type')
            keyword = request.GET.get('keyword')
            limit = min(int(request.GET.get('limit', 100)), 500)
            offset = max(int(request.GET.get('offset', 0)), 0)

            if not spider_type:
                return safe_json_response({
                    'success': False,
                    'error': 'spider_type is required'
                }, status=400)

            base_dir = Path(__file__).resolve().parent.parent.parent
            logs_dir = base_dir / 'logs'
            log_file = logs_dir / f'{spider_type}.log'

            if not logs_dir.exists():
                return safe_json_response({
                    'success': True,
                    'logs': [],
                    'message': 'logs目录不存在'
                })

            if not log_file.exists():
                return safe_json_response({
                    'success': True,
                    'logs': [],
                    'message': '日志文件不存在'
                })

            logs = []
            total_count = 0
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()

                    for line in all_lines:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            log_entry = json.loads(line)
                            if level and log_entry.get('level', '').upper() != level.upper():
                                continue
                            if not self._match_log_type(log_entry, log_type):
                                continue
                            if keyword and keyword.lower() not in log_entry.get('message', '').lower():
                                continue
                            total_count += 1
                        except json.JSONDecodeError:
                            if not keyword or keyword.lower() in line.lower():
                                total_count += 1

                    start_idx = max(0, total_count - offset - limit)
                    end_idx = total_count - offset

                    filtered_logs = []
                    current_idx = 0
                    count_in_range = 0

                    for line in all_lines:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            log_entry = json.loads(line)
                            if level and log_entry.get('level', '').upper() != level.upper():
                                continue
                            if not self._match_log_type(log_entry, log_type):
                                continue
                            if keyword and keyword.lower() not in log_entry.get('message', '').lower():
                                continue
                            current_idx += 1
                            if start_idx < current_idx <= end_idx:
                                filtered_logs.append(log_entry)
                        except json.JSONDecodeError:
                            if not keyword or keyword.lower() in line.lower():
                                current_idx += 1
                                if start_idx < current_idx <= end_idx:
                                    filtered_logs.append({
                                        'message': line,
                                        'raw': True,
                                        'timestamp': None,
                                        'level': 'UNKNOWN'
                                    })

                    logs = filtered_logs

            except Exception as e:
                logger.error(f"读取日志文件失败: {e}")
                return safe_json_response({
                    'success': False,
                    'error': '读取日志失败',
                    'details': str(e)
                }, status=500)

            return safe_json_response({
                'success': True,
                'logs': logs,
                'total': total_count,
                'offset': offset,
                'limit': limit
            })

        except Exception as e:
            logger.error(f"获取爬虫日志失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '获取日志失败',
                'details': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SpiderStatsView(View):
    """爬虫统计API"""

    def get(self, request):
        try:
            spider_type = request.GET.get('type', 'nhsa')

            adapter = SpiderManager.get_adapter(spider_type)
            if not adapter:
                return safe_json_response({
                    'success': False,
                    'error': f'Spider type not found: {spider_type}'
                }, status=404)

            stats = adapter.get_stats()

            try:
                files_dir = adapter.files_dir
                html_dir = adapter.html_dir if hasattr(adapter, 'html_dir') else None

                file_count = 0
                html_count = 0

                if files_dir and files_dir.exists():
                    file_count = count_files_recursive(files_dir)
                if html_dir and html_dir.exists():
                    html_count = count_files_recursive(html_dir)
            except Exception as e:
                logger.warning(f"统计文件数量失败: {e}")

            stats['file_count'] = file_count
            stats['html_count'] = html_count

            if 'categories' not in stats:
                stats['categories'] = {}
            if 'date_range' not in stats:
                stats['date_range'] = {'earliest': None, 'latest': None}

            return safe_json_response({
                'success': True,
                'stats': stats,
                'spider_type': spider_type,
                'spider_name': adapter.get_name()
            })

        except Exception as e:
            logger.error(f"获取爬虫统计失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '获取统计失败',
                'details': str(e)
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SpiderHealthView(View):
    """爬虫健康检查API"""

    def get(self, request):
        try:
            spider_type = request.GET.get('type')

            base_dir = Path(__file__).resolve().parent.parent.parent

            health_info = {
                'redis_connected': False,
                'data_files': {},
                'file_dirs': {},
                'spiders': {}
            }

            try:
                import redis
                r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
                r.ping()
                health_info['redis_connected'] = True
            except Exception as e:
                health_info['redis_error'] = str(e)

            spider_types = ['nhsa', 'wjw']
            for st in spider_types:
                if spider_type and st != spider_type:
                    continue

                data_file = base_dir / 'data' / st / f'{st}_data.json'
                files_dir = base_dir / 'data' / st / f'{st}_files'

                data_exists = data_file.exists()
                file_count = 0

                try:
                    if files_dir.exists():
                        file_count = count_files_recursive(files_dir)
                except Exception:
                    pass

                health_info['data_files'][st] = {
                    'exists': data_exists,
                    'size_bytes': data_file.stat().st_size if data_exists else 0,
                    'size_mb': round(data_file.stat().st_size / 1024 / 1024, 2) if data_exists else 0
                }

                health_info['file_dirs'][st] = {
                    'files_dir_exists': files_dir.exists(),
                    'file_count': file_count,
                    'html_count': 0
                }

                adapter = SpiderManager.get_adapter(st)
                if adapter:
                    status = adapter.get_status()
                    health_info['spiders'][st] = {
                        'name': adapter.get_name(),
                        'status': status.get('status', 'unknown'),
                        'running': status.get('running', False)
                    }

            overall_healthy = (
                health_info['redis_connected'] or
                any(d.get('exists', False) for d in health_info['data_files'].values())
            )

            return safe_json_response({
                'success': True,
                'healthy': overall_healthy,
                'health': health_info,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return safe_json_response({
                'success': False,
                'error': '健康检查失败',
                'details': str(e)
            }, status=500)


def spider_status(request):
    """爬虫状态"""
    return SpiderStatusView.as_view()(request)


def spider_control(request):
    """爬虫控制"""
    return SpiderControlView.as_view()(request)


def crawled_data(request):
    """爬取数据"""
    return CrawledDataView.as_view()(request)


def crawled_files(request):
    """爬取文件"""
    return CrawledFilesView.as_view()(request)


def file_download(request):
    """文件下载"""
    return FileDownloadView.as_view()(request)


def spider_logs(request):
    """爬虫日志"""
    return SpiderLogsView.as_view()(request)


def spider_stats(request):
    """爬虫统计"""
    return SpiderStatsView.as_view()(request)


def spider_list(request):
    """
    获取爬虫项目列表
    GET /api/v1/spiders/list/
    """
    try:
        return safe_json_response({
            'success': True,
            'data': get_all_spider_configs()
        })
    except Exception as e:
        logger.error(f"获取爬虫列表失败: {e}")
        return safe_json_response({
            'success': False,
            'error': '获取爬虫列表失败',
            'details': str(e)
        }, status=500)


def spider_detail(request, spider_id):
    """
    获取爬虫项目详细信息
    GET /api/v1/spiders/{spider_id}/stats/
    """
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
        
        config = get_spider_config_by_id(spider_id)
        if not config:
            return safe_json_response({
                'success': False,
                'error': '爬虫项目不存在'
            }, status=404)

        spider_name = config['spider_name']
        spider_display_name = config['spider_display_name']
        spider_id_value = config['spider_id']

        data_file = base_dir / 'data' / spider_name / f'{spider_name}_data.json'
        files_dir = base_dir / 'data' / spider_name / f'{spider_name}_files'

        collected_links = 0
        crawled_links = 0
        error_count = 0

        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            collected_links += 1
                            if data.get('title'):
                                crawled_links += 1
                        except json.JSONDecodeError:
                            pass

        redis_manager = get_spider_redis_manager(spider_name)
        pending_links = redis_manager.get_links_queue_size() if redis_manager else 0
        error_count = redis_manager.get_error_count() if redis_manager else 0
        redis_status = redis_manager.get_status() if redis_manager else {}
        last_updated = redis_status.get('updated_at')

        file_count = count_files_recursive(files_dir) if files_dir.exists() else 0

        return safe_json_response({
            'success': True,
            'data': {
                'spider_id': spider_id_value or spider_id,
                'spider_name': spider_name,
                'spider_display_name': spider_display_name,
                'collected_links': collected_links,
                'pending_links': pending_links,
                'crawled_links': crawled_links,
                'file_count': file_count,
                'error_count': error_count,
                'last_updated': last_updated
            }
        })

    except Exception as e:
        logger.error(f"获取爬虫详情失败: {e}")
        return safe_json_response({
            'success': False,
            'error': '获取爬虫详情失败',
            'details': str(e)
        }, status=500)


def download_config(request, spider_id):
    """
    下载爬虫项目JSON配置文件
    GET /api/v1/spiders/{spider_id}/json/
    """
    try:
        config = get_spider_config_by_id(spider_id)
        if not config:
            return safe_json_response({
                'success': False,
                'error': '爬虫项目不存在'
            }, status=404)

        spider_name = config['spider_name']
        base_dir = Path(__file__).resolve().parent.parent.parent
        data_file = base_dir / 'data' / spider_name / f'{spider_name}_data.json'

        if not data_file.exists():
            return safe_json_response({
                'success': False,
                'error': '数据文件不存在'
            }, status=404)

        response = FileResponse(
            open(data_file, 'rb'),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{spider_name}_data.json"'
        return response

    except Exception as e:
        logger.error(f"下载配置文件失败: {e}")
        return safe_json_response({
            'success': False,
            'error': '下载失败',
            'details': str(e)
        }, status=500)


def download_item_zip(request, spider_id, item_id):
    """
    下载单个item_id文件夹的ZIP包
    GET /api/v1/spiders/{spider_id}/items/{item_id}/download/
    """
    try:
        config = get_spider_config_by_id(spider_id)
        if not config:
            return safe_json_response({
                'success': False,
                'error': '爬虫项目不存在'
            }, status=404)

        spider_name = config['spider_name']
        base_dir = Path(__file__).resolve().parent.parent.parent
        files_dir = base_dir / 'data' / spider_name / f'{spider_name}_files'
        item_dir = files_dir / str(item_id)

        if not item_dir.exists() or not item_dir.is_dir():
            return safe_json_response({
                'success': False,
                'error': 'item文件夹不存在'
            }, status=404)

        zip_buffer = create_zip_from_directory(item_dir, str(item_id))
        zip_filename = f'{spider_name}_{item_id}.zip'

        response = FileResponse(
            zip_buffer,
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response

    except Exception as e:
        logger.error(f"下载item ZIP失败: {e}")
        return safe_json_response({
            'success': False,
            'error': '下载失败',
            'details': str(e)
        }, status=500)


@csrf_exempt
def batch_download_items(request, spider_id):
    """
    批量下载多个item_id文件夹的ZIP包
    POST /api/v1/spiders/{spider_id}/items/batch-download/
    Body: {"item_ids": ["123", "456", "789"]}
    """
    if request.method != 'POST':
        return safe_json_response({
            'success': False,
            'error': '仅支持POST请求'
        }, status=405)

    try:
        body = json.loads(request.body)
        item_ids = body.get('item_ids', [])

        if not item_ids:
            return safe_json_response({
                'success': False,
                'error': 'item_ids参数不能为空'
            }, status=400)

        if not isinstance(item_ids, list):
            return safe_json_response({
                'success': False,
                'error': 'item_ids必须为数组'
            }, status=400)

        config = get_spider_config_by_id(spider_id)
        if not config:
            return safe_json_response({
                'success': False,
                'error': '爬虫项目不存在'
            }, status=404)

        spider_name = config['spider_name']
        base_dir = Path(__file__).resolve().parent.parent.parent
        files_dir = base_dir / 'data' / spider_name / f'{spider_name}_files'

        if not files_dir.exists():
            return safe_json_response({
                'success': False,
                'error': '文件目录不存在'
            }, status=404)

        zip_buffer, missing_items = create_batch_zip(files_dir, item_ids, spider_name)

        if missing_items and not zip_buffer.getvalue():
            return safe_json_response({
                'success': False,
                'error': '部分item_id不存在',
                'missing_item_ids': missing_items
            }, status=404)

        # timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'{spider_name}_batch_{len(item_ids)}.zip'

        response = FileResponse(
            zip_buffer,
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        return response

    except json.JSONDecodeError:
        return safe_json_response({
            'success': False,
            'error': '请求体必须为有效的JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"批量下载失败: {e}")
        return safe_json_response({
            'success': False,
            'error': '下载失败',
            'details': str(e)
        }, status=500)


def spider_health(request):
    """爬虫健康检查"""
    return SpiderHealthView.as_view()(request)
