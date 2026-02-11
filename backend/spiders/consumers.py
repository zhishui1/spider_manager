"""
WebSocket consumers for real-time spider status updates.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .adapters import SpiderManager


class SpiderStatusConsumer(AsyncWebsocketConsumer):
    """爬虫状态WebSocket消费者"""
    
    async def connect(self):
        await self.accept()
        self.group_name = 'spider_status'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'get_status':
                status = SpiderManager.get_all_status()
                await self.send(text_data=json.dumps({
                    'type': 'status',
                    'data': status
                }))
            elif action == 'start':
                spider_type = data.get('spider_type')
                if SpiderManager.start_spider(spider_type):
                    await self.send(text_data=json.dumps({
                        'type': 'success',
                        'message': f'{spider_type} started'
                    }))
            elif action == 'stop':
                spider_type = data.get('spider_type')
                if SpiderManager.stop_spider(spider_type):
                    await self.send(text_data=json.dumps({
                        'type': 'success',
                        'message': f'{spider_type} stopped'
                    }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def spider_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'data': event['data']
        }))
