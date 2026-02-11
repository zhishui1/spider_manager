"""
国家医保局爬虫模块
"""

from .crawler import NHSACrawler
from .config import SPIDER_NAME, SPIDER_DISPLAY_NAME

__all__ = ['NHSACrawler', 'SPIDER_NAME', 'SPIDER_DISPLAY_NAME']
