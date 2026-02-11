"""
URL configuration for API.
"""

from django.urls import path
from django.http import JsonResponse

def health_check(request):
    """健康检查"""
    return JsonResponse({
        'status': 'ok',
        'message': 'Spider Manager API is running'
    })

def index(request):
    """首页"""
    return JsonResponse({
        'status': 'ok',
        'message': 'Spider Manager API is running',
        'docs': '/api/v1/',
        'health': '/api/v1/health/'
    })

urlpatterns = [
    path('', index, name='index'),
    path('health/', health_check, name='health_check'),
]
