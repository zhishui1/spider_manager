"""
定时任务管理模块
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from croniter import croniter
from backend.spiders.adapters import SpiderManager


class ScheduledTask:
    """定时任务类"""
    
    def __init__(self, spider_type: str, cron_expression: str, task_id: str = None):
        self.task_id = task_id or f"task_{int(time.time() * 1000)}"
        self.spider_type = spider_type
        self.cron_expression = cron_expression
        self.cron = croniter(cron_expression, datetime.now())
        self.next_run = self.cron.get_next(datetime)
        self.last_run: Optional[datetime] = None
        self.status = 'pending'
        self.config = {}
    
    def get_next_run(self) -> datetime:
        """获取下次执行时间"""
        return self.next_run
    
    def execute(self) -> bool:
        """执行任务"""
        try:
            self.status = 'running'
            SpiderManager.start_spider(self.spider_type)
            self.last_run = datetime.now()
            self.cron = croniter(self.cron_expression, self.last_run)
            self.next_run = self.cron.get_next(datetime)
            self.status = 'completed'
            return True
        except Exception as e:
            self.status = 'error'
            return False


class TaskScheduler:
    """任务调度器"""
    
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
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        self._initialized = True
    
    def add_task(self, spider_type: str, cron_expression: str, task_id: str = None) -> ScheduledTask:
        """添加定时任务"""
        task = ScheduledTask(spider_type, cron_expression, task_id)
        self.tasks[task.task_id] = task
        return task
    
    def remove_task(self, task_id: str) -> bool:
        """删除定时任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[ScheduledTask]:
        """获取所有任务"""
        return list(self.tasks.values())
    
    def start(self):
        """启动调度器"""
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        print("Task scheduler started")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("Task scheduler stopped")
    
    def _run_scheduler(self):
        """调度器主循环"""
        while self.running:
            now = datetime.now()
            
            for task_id, task in list(self.tasks.items()):
                if task.next_run <= now and task.status != 'running':
                    print(f"Executing task {task_id}: {task.spider_type}")
                    task.execute()
            
            time.sleep(1)
    
    def get_schedule_status(self) -> Dict[str, Dict]:
        """获取调度状态"""
        status = {}
        for task_id, task in self.tasks.items():
            status[task_id] = {
                'spider_type': task.spider_type,
                'cron_expression': task.cron_expression,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'status': task.status,
            }
        return status


scheduler = TaskScheduler()
