from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, MeView,
    ProfileView, ChangePasswordView,
    ForgotPasswordView, ResetPasswordView,
)

urlpatterns = [
    # Auth
    path('auth/register/',        RegisterView.as_view(),       name='auth-register'),
    path('auth/login/',           LoginView.as_view(),          name='auth-login'),
    path('auth/logout/',          LogoutView.as_view(),         name='auth-logout'),
    path('auth/me/',              MeView.as_view(),             name='auth-me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('auth/reset-password/',  ResetPasswordView.as_view(),  name='auth-reset-password'),

    # Profile
    path('profile/',        ProfileView.as_view(), name='user-profile'),
    path('profile/update/', ProfileView.as_view(), name='user-profile-update'),
]
