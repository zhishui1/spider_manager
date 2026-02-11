"""
URL configuration for spider_manager backend project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('backend.api.urls')),
    path('api/v1/spiders/', include('backend.spiders.urls')),
]
