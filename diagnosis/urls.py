from django.urls import path
from .views import diagnosis_detail, diagnosis_list

urlpatterns = [
    path('diagnosis/',                  diagnosis_list,   name='diagnosis-list'),
    path('diagnosis/<str:analysis_id>/',diagnosis_detail, name='diagnosis-detail'),
]
