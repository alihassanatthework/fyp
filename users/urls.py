from django.urls import path
from .views import (
    RegisterView, LoginView, LogoutView, MeView,
    ProfileView, ChangePasswordView,
    ForgotPasswordView, ResetPasswordView,
    UserListView, UserRoleView, MyRoleView,
    UpgradeAccountView,
    PaymentInitView, PaymentWebhookView, PaymentVerifyView,
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

    # Account tier
    path('account/upgrade/', UpgradeAccountView.as_view(), name='account-upgrade'),

    # Payments (Safepay: cards + Easypaisa + JazzCash)
    path('payments/init/',    PaymentInitView.as_view(),    name='payment-init'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('payments/verify/',  PaymentVerifyView.as_view(),  name='payment-verify'),

    # Role
    path('auth/my-role/',              MyRoleView.as_view(),  name='my-role'),

    # Admin
    path('admin/users/',               UserListView.as_view(),  name='admin-users'),
    path('admin/users/<int:pk>/role/', UserRoleView.as_view(),  name='admin-user-role'),
]
