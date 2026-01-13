"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from image_analysis.views import AnalyzeImageView

urlpatterns = [
    path('admin/', admin.site.urls),
    # path('upload/', AnalyzeImageView.as_view(), name='upload_force_test'),
    path('upload/', AnalyzeImageView.as_view(), name='upload'),
    
    # Frontend pages
    path('', include('frontend.urls')),
    
    # API endpoints (to be implemented)
    # path('api/auth/', include('users.urls')),
    # path('api/users/', include('users.urls')),
    # path('api/analysis/', include('image_analysis.urls')),
    # path('api/diagnosis/', include('diagnosis.urls')),
    # path('api/recommendations/', include('recommendations.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
