"""
URL configuration for spiders app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.spider_status, name='spider_status'),
    path('control/', views.spider_control, name='spider_control'),
    path('data/', views.crawled_data, name='crawled_data'),
    path('files/', views.crawled_files, name='crawled_files'),
    path('download/', views.file_download, name='file_download'),
    path('logs/', views.spider_logs, name='spider_logs'),
    path('stats/', views.spider_stats, name='spider_stats'),
    path('list/', views.spider_list, name='spider_list'),
    path('<str:spider_id>/stats/', views.spider_detail, name='spider_detail'),
    path('<str:spider_id>/json/', views.download_config, name='download_config'),
    path('<str:spider_id>/items/<str:item_id>/download/', views.download_item_zip, name='download_item_zip'),
    path('<str:spider_id>/items/batch-download/', views.batch_download_items, name='batch_download_items'),
]
