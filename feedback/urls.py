from django.urls import path
from .views import submit_feedback, get_feedback

urlpatterns = [
    path('feedback/<str:analysis_id>/', get_feedback,    name='get-feedback'),
    path('feedback/<str:analysis_id>/submit/', submit_feedback, name='submit-feedback'),
]
