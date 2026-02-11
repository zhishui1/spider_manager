"""
爬虫通用工具函数
所有爬虫项目共享的工具函数
"""

import time
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CRAWLERS_DIR = BASE_DIR / 'backend' / 'spiders' / 'crawlers'
DATA_DIR = BASE_DIR / 'data'


def get_data_dir(spider_name: str) -> Path:
    """获取爬虫数据目录
    
    根据爬虫名称返回对应的数据存储目录。
    例如：spider_name='nhsa' 返回 data/nhsa
    
    Args:
        spider_name: 爬虫名称，如 'nhsa', 'wjw' 等
    
    Returns:
        Path 对象，数据目录路径
    """
    return DATA_DIR / spider_name


def get_spider_files_base_dir(spider_name: str) -> Path:
    """获取爬虫附件文件基础目录
    
    根据爬虫名称返回附件文件的基础存储目录。
    
    Args:
        spider_name: 爬虫名称，如 'nhsa'
    
    Returns:
        Path 对象，附件基础目录，如 data/nhsa/nhsa_files
    """
    return DATA_DIR / spider_name / f'{spider_name}_files'


def get_item_dir(spider_name: str, item_id: int) -> Path:
    """获取单个数据项的文件存储目录
    
    每个采集的数据项有独立的文件夹，用于存储其附件文件。
    命名格式：{item_id}/
    
    Args:
        spider_name: 爬虫名称，如 'nhsa'
        item_id: 数据项ID（毫秒级时间戳）
    
    Returns:
        Path 对象，存储目录，如 data/nhsa/nhsa_files/1769153573123/
    """
    files_dir = get_spider_files_base_dir(spider_name)
    return files_dir / str(item_id)


def get_data_file(spider_name: str) -> Path:
    """获取爬虫数据文件路径
    
    返回爬虫采集数据的 JSON 文件路径。
    每条采集数据以 JSON Lines 格式存储（每行一条 JSON）。
    
    Args:
        spider_name: 爬虫名称，如 'nhsa'
    
    Returns:
        Path 对象，数据文件路径，如 data/nhsa/nhsa_data.json
    """
    return DATA_DIR / spider_name / f'{spider_name}_data.json'


def ensure_directories(spider_name: str) -> Tuple[Path, Path]:
    """确保爬虫所需目录存在
    
    创建爬虫运行所需的数据目录和附件基础目录。
    如果目录已存在则不会重复创建。
    
    Args:
        spider_name: 爬虫名称，如 'nhsa'
    
    Returns:
        元组 (data_dir, files_base_dir)
        - data_dir: 数据目录
        - files_base_dir: 附件基础目录
    """
    data_dir = get_data_dir(spider_name)
    files_base_dir = get_spider_files_base_dir(spider_name)
    
    data_dir.mkdir(parents=True, exist_ok=True)
    files_base_dir.mkdir(parents=True, exist_ok=True)
    
    return data_dir, files_base_dir


def ensure_item_dir(spider_name: str, item_id: int) -> Path:
    """确保数据项的存储目录存在
    
    Args:
        spider_name: 爬虫名称
        item_id: 数据项ID
    
    Returns:
        Path 对象，数据项存储目录
    """
    item_dir = get_item_dir(spider_name, item_id)
    item_dir.mkdir(parents=True, exist_ok=True)
    return item_dir


def generate_item_id() -> int:
    """生成毫秒级时间戳唯一ID
    
    为每条采集数据生成全局唯一的时间戳ID。
    格式为毫秒级 Unix 时间戳，可保证高并发下的唯一性。
    
    Returns:
        int 类型的毫秒时间戳，如 1769153573123
    """
    return int(datetime.now().timestamp() * 1000)


def to_relative_path(absolute_path: str, base_dir: Path = BASE_DIR) -> str:
    """将绝对路径转换为相对于项目根目录的相对路径
    
    用于将下载文件的绝对路径转换为相对路径，
    以便在不同环境下保持路径的一致性。
    
    Args:
        absolute_path: 文件的绝对路径
        base_dir: 基准目录，默认为项目根目录
    
    Returns:
        相对路径字符串，使用正斜杠分隔
        例如：data/nhsa/nhsa_files/1769153573123/1.pdf
    """
    from pathlib import Path as PathLib
    abs_path = PathLib(absolute_path)
    try:
        rel_path = abs_path.relative_to(base_dir)
        return str(rel_path).replace('\\', '/')
    except ValueError:
        return str(abs_path).replace('\\', '/')


def random_delay(min_delay: float, max_delay: float) -> None:
    """随机延迟一段时间
    
    在请求之间添加随机延迟，模拟人类访问行为，
    避免高频请求被目标网站封禁。
    
    Args:
        min_delay: 最小延迟秒数
        max_delay: 最大延迟秒数
    
    Example:
        random_delay(1, 2)  # 随机等待1-2秒
    """
    import random
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def human_like_delay() -> None:
    """人类-like随机延迟
    
    比基础延迟更随机的延迟模式，模拟更自然的访问间隔。
    延迟范围：0.5-2.5秒
    
    作用：
        - 降低被反爬虫机制检测的风险
        - 减少对目标服务器的访问压力
    """
    import random
    base = random.uniform(0.5, 1.5)
    jitter = random.uniform(0, 0.5)
    time.sleep(base + jitter)


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        清理后的文件名
    """
    import re
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip()
    if len(filename) > 200:
        filename = filename[:200]
    return filename


def get_file_suffix(url: str, default: str = 'bin') -> str:
    """从URL获取文件扩展名
    
    Args:
        url: 文件URL
        default: 默认扩展名
    
    Returns:
        文件扩展名（小写），如 'pdf', 'doc', 'txt' 等
    """
    from urllib.parse import urlparse, unquote, parse_qs
    parsed = urlparse(url)
    path = unquote(parsed.path)
    query = parse_qs(parsed.query)
    
    filename_from_query = query.get('filename', [''])[0]
    if filename_from_query and '.' in filename_from_query:
        suffix = filename_from_query.split('.')[-1].lower()
        if len(suffix) <= 10:
            return suffix
    
    if '.' in path:
        suffix = path.split('.')[-1].lower()
        if len(suffix) <= 10:
            return suffix
    return default


def save_content_to_file(content: str, item_dir: Path, filename: str, encoding: str = 'utf-8') -> str:
    """保存文本内容到文件
    
    Args:
        content: 文本内容
        item_dir: 存储目录
        filename: 文件名
        encoding: 文件编码
    
    Returns:
        相对路径
    """
    file_path = item_dir / sanitize_filename(filename)
    with open(file_path, 'w', encoding=encoding, errors='ignore') as f:
        f.write(content)
    return to_relative_path(str(file_path))


def download_file(url: str, item_dir: Path, filename: str, timeout: int = 60, headers: dict = None) -> str:
    """下载文件到指定目录
    
    Args:
        url: 文件URL
        item_dir: 存储目录
        filename: 文件名（不含扩展名）
        timeout: 超时时间（秒）
        headers: 请求头
    
    Returns:
        相对路径，下载失败返回 None
    """
    import requests
    
    suffix = get_file_suffix(url)
    if not filename.endswith(f'.{suffix}'):
        filename = f'{filename}.{suffix}'
    
    file_path = item_dir / sanitize_filename(filename)
    
    try:
        resp = requests.get(url, timeout=timeout, headers=headers or {}, stream=True)
        resp.raise_for_status()
        
        total_size = int(resp.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(file_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded_size += len(chunk)
        
        return to_relative_path(str(file_path))
    except Exception as e:
        print(f"[下载失败] {url}: {e}")
        return None


def request_get_with_retry(
    url: str,
    headers: dict = None,
    proxies: dict = None,
    timeout: int = 10,
    retry_times: int = 3,
    retry_delay: int = 10,
    logger = None,
    error_recorder = None,
    cookies: dict = None
):
    """发送GET请求（带重试机制）
    
    Args:
        url: 请求URL
        headers: 请求头
        proxies: 代理配置
        timeout: 超时时间（秒）
        retry_times: 重试次数
        retry_delay: 重试间隔（秒）
        logger: 日志记录器
        error_recorder: 错误记录函数
        cookies: 请求Cookie
    
    Returns:
        requests.Response 对象，失败返回 None
    """
    import requests
    
    resp = None
    for i in range(1, retry_times + 1):
        try:
            resp = requests.get(
                url,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                verify=False,
                cookies=cookies
            )
            if resp.status_code == 200:
                return resp
            elif resp.status_code == 404:
                if logger:
                    logger.warning(f'页面不存在: {url}')
                break
            else:
                if logger:
                    logger.warning(f'状态码 {resp.status_code}，重试第{i}次: {url}')
                if i == retry_times and error_recorder:
                    error_recorder('retry_exhausted', url, f'重试{i}次后失败')
                time.sleep(retry_delay)
        except Exception as e:
            if logger:
                logger.error(f'请求错误: {e}，重试第{i}次: {url}')
            if i == retry_times and error_recorder:
                error_recorder('retry_exhausted', url, str(e))
            time.sleep(retry_delay)
    return resp


def request_post_with_retry(
    url: str,
    data: dict,
    params: dict = None,
    headers: dict = None,
    proxies: dict = None,
    timeout: int = 10,
    retry_times: int = 3,
    retry_delay: int = 10,
    logger = None,
    error_recorder = None
):
    """发送POST请求（带重试机制）
    
    Args:
        url: 请求URL
        data: POST数据
        params: URL参数
        headers: 请求头
        proxies: 代理配置
        timeout: 超时时间（秒）
        retry_times: 重试次数
        retry_delay: 重试间隔（秒）
        logger: 日志记录器
        error_recorder: 错误记录函数
    
    Returns:
        requests.Response 对象，失败返回 None
    """
    import requests
    
    resp = None
    for i in range(1, retry_times + 1):
        try:
            resp = requests.post(
                url,
                data=data,
                params=params,
                headers=headers,
                proxies=proxies,
                timeout=timeout,
                verify=False
            )
            if resp.status_code == 200:
                return resp
            else:
                if logger:
                    logger.warning(f'POST状态码 {resp.status_code}，重试第{i}次: {url}')
                if i == retry_times and error_recorder:
                    error_recorder('retry_exhausted', url, f'重试{i}次后失败')
                time.sleep(retry_delay)
        except Exception as e:
            if logger:
                logger.error(f'POST请求错误: {e}，重试第{i}次: {url}')
            if i == retry_times and error_recorder:
                error_recorder('retry_exhausted', url, str(e))
            time.sleep(retry_delay)
    return resp


def decode_response(resp) -> str:
    """解码HTML响应，自动检测编码
    
    Args:
        resp: requests.Response 对象
    
    Returns:
        解码后的 HTML 字符串
    """
    import re
    html_text = resp.text
    charset = re.findall(r'charset="(.*?)"', html_text)
    if charset:
        charset = charset[0]
        html = resp.content.decode(charset, errors='ignore')
    elif resp.encoding == "ISO-8859-1":
        resp.encoding = None
        html = resp.text
    else:
        html = resp.text
    return html


def html_to_xpath(html: str):
    """使用XPath解析HTML
    
    Args:
        html: HTML 字符串
    
    Returns:
        etree.HTML 文档对象
    """
    from lxml import etree
    return etree.HTML(html)


def parse_response(resp):
    """解析响应内容（用于 XML/HTML 响应）
    
    Args:
        resp: requests.Response 对象
    
    Returns:
        etree.HTML 文档对象，解析失败返回 None
    """
    import re
    try:
        content = resp.text
        content = re.sub(r'<\?xml[^>]*\?>', '', content)
        content = content.strip()
        if not content:
            return None
        return html_to_xpath(content)
    except Exception as e:
        print(f"[解析响应失败] {e}")
        return None
