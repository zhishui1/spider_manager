"""
文件操作工具模块
提供ZIP打包、文件下载等工具函数
"""

import os
import io
import zipfile
import shutil
from pathlib import Path
from typing import List, Optional


def create_zip_from_directory(source_dir: Path, arcname_prefix: str = '') -> io.BytesIO:
    """
    将目录打包为ZIP文件

    Args:
        source_dir: 源目录路径
        arcname_prefix: 压缩包内文件名的前缀

    Returns:
        ZIP文件的BytesIO对象
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                if arcname_prefix:
                    archive_name = f"{arcname_prefix}/{file_path.name}"
                else:
                    archive_name = file_path.name
                zip_file.write(file_path, archive_name)

    zip_buffer.seek(0)
    return zip_buffer


def create_zip_from_files(files: List[dict], base_dir: Path) -> io.BytesIO:
    """
    根据文件列表创建ZIP文件

    Args:
        files: 文件信息列表 [{'name': 'filename', 'path': '/path/to/file'}]
        base_dir: 基础目录

    Returns:
        ZIP文件的BytesIO对象
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_info in files:
            file_path = base_dir / file_info['path']
            if file_path.exists() and file_path.is_file():
                archive_name = file_info.get('name', file_path.name)
                zip_file.write(file_path, archive_name)

    zip_buffer.seek(0)
    return zip_buffer


def create_batch_zip(
    spider_files_dir: Path,
    item_ids: List[str],
    spider_name: str
) -> tuple[io.BytesIO, List[str]]:
    """
    批量打包多个item文件夹为ZIP

    Args:
        spider_files_dir: 爬虫文件目录 (e.g., data/nhsa/nhsa_files)
        item_ids: 要打包的item_id列表
        spider_name: 爬虫名称

    Returns:
        (ZIP文件的BytesIO对象, 缺失的item_id列表)
    """
    zip_buffer = io.BytesIO()
    missing_items = []

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for item_id in item_ids:
            item_dir = spider_files_dir / str(item_id)
            if item_dir.exists() and item_dir.is_dir():
                for root, dirs, files in os.walk(item_dir):
                    for file in files:
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(spider_files_dir)
                        zip_file.write(file_path, str(relative_path))
            else:
                missing_items.append(item_id)

    zip_buffer.seek(0)
    return zip_buffer, missing_items


def get_file_size_str(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 字节大小

    Returns:
        格式化后的大小字符串 (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def safe_filename(filename: str) -> str:
    """
    清理文件名，移除不安全字符

    Args:
        filename: 原始文件名

    Returns:
        清理后的安全文件名
    """
    unsafe_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()
