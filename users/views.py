import logging

from django.contrib.auth import authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password as dj_validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import UserProfile, MedicalHistory
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    UserProfileSerializer,
    MedicalHistorySerializer,
)

logger = logging.getLogger(__name__)


def _tokens_for_user(user):
    """Return a dict with 'access' and 'refresh' JWT strings."""
    refresh = RefreshToken.for_user(user)
    return {'access': str(refresh.access_token), 'refresh': str(refresh)}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

class RegisterView(APIView):
    """POST /api/auth/register/  — create account, return tokens immediately."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        return Response(
            {'user': UserSerializer(user).data, **_tokens_for_user(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/auth/login/  — email + password → tokens."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'error': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Resolve email → username (we store email as username at registration)
        try:
            user_obj = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = authenticate(request, username=user_obj.username, password=password)
        if not user:
            return Response(
                {'error': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        logger.info("User logged in: %s", user.email)
        return Response(
            {'user': UserSerializer(user).data, **_tokens_for_user(user)},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """POST /api/auth/logout/  — blacklist the refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            pass  # Already invalid or blacklisted — still treat as success

        logger.info("User logged out: %s", request.user.email)
        return Response({}, status=status.HTTP_200_OK)


class MeView(APIView):
    """GET /api/auth/me/  — return the current user's data (requires token)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, 'profile', None)
        med = getattr(user, 'medical_history', None)
        return Response({
            'user': UserSerializer(user).data,
            'profile': UserProfileSerializer(profile).data if profile else None,
            'medical_history': MedicalHistorySerializer(med).data if med else None,
        })


# ---------------------------------------------------------------------------
# Change password
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    """POST /api/auth/change-password/  — change password for authenticated user."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get('old_password', '')
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not old_password or not new_password or not confirm_password:
            return Response(
                {'error': 'old_password, new_password, and confirm_password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'New passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dj_validate_password(new_password, request.user)
        except Exception as exc:
            return Response(
                {'error': list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_password)
        request.user.save()
        logger.info("Password changed for user: %s", request.user.email)

        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Profile endpoint
# ---------------------------------------------------------------------------

class ProfileView(APIView):
    """GET/PATCH /api/profile/  — read or update profile + medical history."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        med, _ = MedicalHistory.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'profile': UserProfileSerializer(profile).data,
            'medical_history': MedicalHistorySerializer(med).data,
        })

    def patch(self, request):
        user = request.user

        # Update name fields if provided
        user_data = request.data.get('user', {})
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        user.save()

        # Update UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile_data = request.data.get('profile', {})
        p_ser = UserProfileSerializer(profile, data=profile_data, partial=True)
        if p_ser.is_valid():
            p_ser.save()

        # Update MedicalHistory
        med, _ = MedicalHistory.objects.get_or_create(user=user)
        med_data = request.data.get('medical_history', {})
        m_ser = MedicalHistorySerializer(med, data=med_data, partial=True)
        if m_ser.is_valid():
            m_ser.save()

        return Response({
            'user': UserSerializer(user).data,
            'profile': UserProfileSerializer(profile).data,
            'medical_history': MedicalHistorySerializer(med).data,
        })


# ---------------------------------------------------------------------------
# Password Reset (Forgot Password)
# ---------------------------------------------------------------------------

class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/
    Body: { "email": "user@example.com" }

    Sends a password-reset link to the user's email.
    Always returns 200 (even if email not found) to prevent user enumeration.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'error': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Return 200 regardless — don't reveal whether email exists
            return Response(
                {'message': 'If an account with that email exists, a reset link has been sent.'},
                status=status.HTTP_200_OK,
            )

        # Build a secure one-time token using Django's built-in token generator
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_url = f'{frontend_url}/reset-password/{uid}/{token}/'

        subject = 'Reset your AI Skin Assistant password'
        message = (
            f'Hi {user.first_name or user.email},\n\n'
            f'You requested a password reset for your AI Skin Assistant account.\n\n'
            f'Click the link below to set a new password:\n'
            f'{reset_url}\n\n'
            f'This link expires in 1 hour.\n\n'
            f'If you did not request this, you can safely ignore this email.\n\n'
            f'— AI Skin Assistant Team'
        )

        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            logger.info("Password reset email sent to: %s", user.email)
        except Exception as exc:
            logger.error("Failed to send reset email to %s: %s", user.email, exc)
            return Response(
                {'error': 'Failed to send email. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {'message': 'If an account with that email exists, a reset link has been sent.'},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/
    Body: { "uid": "...", "token": "...", "new_password": "...", "confirm_password": "..." }

    Validates the token and sets the new password.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        uid              = request.data.get('uid', '')
        token            = request.data.get('token', '')
        new_password     = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not all([uid, token, new_password, confirm_password]):
            return Response(
                {'error': 'uid, token, new_password, and confirm_password are all required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'Passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decode the user ID
        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user    = User.objects.get(pk=user_pk)
        except (ValueError, TypeError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid reset link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify the token (single-use, expires after PASSWORD_RESET_TIMEOUT seconds)
        if not default_token_generator.check_token(user, token):
            return Response(
                {'error': 'This reset link has expired or already been used. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate password strength
        try:
            dj_validate_password(new_password, user)
        except Exception as exc:
            return Response(
                {'error': list(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        logger.info("Password reset successfully for user: %s", user.email)

        return Response(
            {'message': 'Password reset successfully. You can now log in with your new password.'},
            status=status.HTTP_200_OK,
        )
