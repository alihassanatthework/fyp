from django.urls import path
from . import views

urlpatterns = [
    path('providers/',          views.list_providers,   name='provider-list'),
    path('providers/nearby/',   views.nearby_providers, name='provider-nearby'),
    path('providers/<int:pk>/', views.provider_detail,  name='provider-detail'),
]
