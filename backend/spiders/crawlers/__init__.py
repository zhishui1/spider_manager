"""
爬虫配置注册中心
用于集中管理所有爬虫项目的配置
"""

import re
from pathlib import Path
from typing import Dict, List, Optional

_spiders_registry: List[Dict] = []


def register_spider(spider_id: str, spider_name: str, spider_display_name: str) -> None:
    """
    注册爬虫配置
    """
    _spiders_registry.append({
        'spider_id': spider_id,
        'spider_name': spider_name,
        'spider_display_name': spider_display_name
    })


def get_all_spiders() -> List[Dict]:
    """获取所有注册的爬虫配置"""
    return _spiders_registry.copy()


def get_spider_by_id(spider_id: str) -> Optional[Dict]:
    """根据 spider_id 获取爬虫配置"""
    for spider in _spiders_registry:
        if spider_id.startswith(spider['spider_name']):
            return spider
    return None


def extract_config_var(content: str, var_name: str) -> Optional[str]:
    """从Python代码中提取变量值"""
    patterns = [
        rf'{var_name}\s*=\s*["\']([^"\']+)["\']',
        rf'{var_name}\s*=\s*str\(([^)]+)\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
    return None


def auto_discover_spiders() -> None:
    """
    自动发现并注册所有爬虫模块
    """
    crawlers_dir = Path(__file__).parent
    
    for item_path in crawlers_dir.iterdir():
        if item_path.is_dir():
            config_path = item_path / 'config.py'
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    spider_id = extract_config_var(content, 'SPIDER_ID')
                    spider_name = extract_config_var(content, 'SPIDER_NAME')
                    spider_display_name = extract_config_var(content, 'SPIDER_DISPLAY_NAME')
                    
                    if spider_id and spider_name:
                        register_spider(
                            spider_id=spider_id,
                            spider_name=spider_name,
                            spider_display_name=spider_display_name or spider_name
                        )
                except Exception as e:
                    pass


auto_discover_spiders()
