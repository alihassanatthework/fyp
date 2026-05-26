from django.urls import path, include
from image_analysis.views import AnalyzeImageView
from rest_framework_simplejwt.views import TokenRefreshView

from .views import analysis_history, analysis_detail, analysis_stats

urlpatterns = [
    # Auth + profile (register, login, logout, me, profile)
    path('', include('users.urls')),

    # JWT silent refresh — called automatically by the Axios interceptor
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Feedback
    path('', include('feedback.urls')),

    # Diagnosis reports
    path('', include('diagnosis.urls')),

    # Recommendations
    path('', include('recommendations.urls')),

    # Skin/scalp image upload + AI processing (returns JSON when client Accepts JSON)
    path('analysis/upload/', AnalyzeImageView.as_view(), name='analysis-upload'),

    # Dashboard stats summary
    path('analysis/stats/', analysis_stats, name='analysis-stats'),

    # Analysis history
    path('analysis/history/', analysis_history, name='analysis-history'),

    # Analysis detail + delete
    path('analysis/<str:analysis_id>/', analysis_detail, name='analysis-detail'),

    # Phase 2 — Providers & Bookings
    path('', include('providers.urls')),
    path('', include('bookings.urls')),

    # Phase 2 — Makeup & Fashion
    path('', include('makeup.urls')),
    path('', include('fashion.urls')),
]