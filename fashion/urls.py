from django.urls import path
from . import views

urlpatterns = [
    path('fashion/suggest/', views.fashion_suggest, name='fashion-suggest'),
    path('fashion/history/', views.fashion_history, name='fashion-history'),
]
