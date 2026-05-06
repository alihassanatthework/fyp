from django.urls import path
from .views import recommendations_for_analysis, all_recommendations

urlpatterns = [
    path('recommendations/',                       all_recommendations,          name='recommendations-all'),
    path('recommendations/<str:analysis_id>/',     recommendations_for_analysis, name='recommendations-detail'),
]
