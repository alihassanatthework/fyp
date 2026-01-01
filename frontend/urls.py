from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('upload/', views.upload_image, name='upload'),
    path('results/<int:analysis_id>/', views.analysis_results, name='results'),
    path('results/', views.analysis_results, name='results'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit-medical-history/', views.edit_medical_history, name='edit_medical_history'),
    path('history/', views.history, name='history'),
]

