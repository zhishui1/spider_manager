"""
Database models for the spider manager platform.
"""

from django.db import models
from django.utils import timezone


class Spider(models.Model):
    """爬虫模型"""
    STATUS_CHOICES = [
        ('idle', '空闲'),
        ('running', '运行中'),
        ('paused', '已暂停'),
        ('error', '错误'),
    ]
    
    SPIDER_TYPES = [
        ('nhsa', '国家医保局爬虫'),
        ('wjw', '卫生健康委爬虫'),
    ]
    
    name = models.CharField('爬虫名称', max_length=100)
    spider_type = models.CharField('爬虫类型', max_length=20, choices=SPIDER_TYPES)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='idle')
    config = models.JSONField('配置参数', default=dict, blank=True)
    frequency = models.IntegerField('爬取频率(秒)', default=3600)
    last_run = models.DateTimeField('上次运行时间', null=True, blank=True)
    last_success = models.DateTimeField('上次成功时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '爬虫'
        verbose_name_plural = '爬虫'
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class CrawlTask(models.Model):
    """爬取任务模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    spider = models.ForeignKey(Spider, on_delete=models.CASCADE, related_name='tasks')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    start_time = models.DateTimeField('开始时间', null=True, blank=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    items_crawled = models.IntegerField('爬取数量', default=0)
    items_success = models.IntegerField('成功数量', default=0)
    error_message = models.TextField('错误信息', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '爬取任务'
        verbose_name_plural = '爬取任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.spider.name} - {self.get_status_display()}"


class CrawledData(models.Model):
    """爬取数据模型"""
    spider = models.ForeignKey(Spider, on_delete=models.CASCADE, related_name='data')
    task = models.ForeignKey(CrawlTask, on_delete=models.SET_NULL, null=True, related_name='data')
    category = models.CharField('类别', max_length=100, blank=True)
    title = models.CharField('标题', max_length=500)
    content = models.TextField('内容', blank=True)
    url = models.URLField('来源URL')
    file_paths = models.JSONField('文件路径', default=list, blank=True)
    metadata = models.JSONField('元数据', default=dict, blank=True)
    crawled_at = models.DateTimeField('爬取时间', default=timezone.now)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '爬取数据'
        verbose_name_plural = '爬取数据'
        indexes = [
            models.Index(fields=['spider', 'crawled_at']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return self.title[:50]


class SpiderLog(models.Model):
    """爬虫日志模型"""
    LEVEL_CHOICES = [
        ('debug', '调试'),
        ('info', '信息'),
        ('warning', '警告'),
        ('error', '错误'),
    ]
    
    spider = models.ForeignKey(Spider, on_delete=models.CASCADE, related_name='logs')
    task = models.ForeignKey(CrawlTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='logs')
    level = models.CharField('日志级别', max_length=20, choices=LEVEL_CHOICES)
    message = models.TextField('日志消息')
    extra = models.JSONField('额外信息', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '爬虫日志'
        verbose_name_plural = '爬虫日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['spider', 'created_at']),
            models.Index(fields=['level']),
        ]


class ScheduledTask(models.Model):
    """定时任务模型"""
    STATUS_CHOICES = [
        ('active', '激活'),
        ('paused', '暂停'),
        ('disabled', '禁用'),
    ]
    
    spider = models.ForeignKey(Spider, on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField('任务名称', max_length=100)
    cron_expression = models.CharField('Cron表达式', max_length=100)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='active')
    last_run = models.DateTimeField('上次执行', null=True, blank=True)
    next_run = models.DateTimeField('下次执行', null=True, blank=True)
    config = models.JSONField('配置', default=dict, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '定时任务'
        verbose_name_plural = '定时任务'
    
    def __str__(self):
        return f"{self.name} ({self.cron_expression})"
