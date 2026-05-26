from django.urls import path
from . import views

urlpatterns = [
    path('makeup/suggest/', views.makeup_suggest,  name='makeup-suggest'),
    path('makeup/history/', views.makeup_history,  name='makeup-history'),
]
