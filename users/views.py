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

from .models import UserProfile, MedicalHistory, UserRole
from .permissions import IsAdmin
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
        try:
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
            except User.MultipleObjectsReturned:
                # Defensive: duplicate emails in legacy data — fall back to .filter().first()
                user_obj = User.objects.filter(email__iexact=email).first()
                if not user_obj:
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

            try:
                tokens = _tokens_for_user(user)
            except Exception as exc:
                logger.exception("Token generation failed for %s: %s", user.email, exc)
                return Response(
                    {'error': 'Could not issue session token. Please try again.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            logger.info("User logged in: %s", user.email)
            return Response(
                {'user': UserSerializer(user).data, **tokens},
                status=status.HTTP_200_OK,
            )

        except Exception as exc:
            # Last-resort guard so the user never sees a raw HTML 500 page.
            logger.exception("Unexpected error in LoginView: %s", exc)
            return Response(
                {'error': 'Something went wrong. Please try again in a moment.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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

        # ── Build the multipart transactional email ──
        # Plain-text + HTML version, plus headers that flag this as a
        # transactional (one-to-one, user-initiated) message so Gmail
        # routes it to Primary instead of Promotions / Spam.
        from django.core.mail import EmailMultiAlternatives

        first_name = user.first_name or user.email.split('@')[0]
        subject = 'Reset your ME Skin Assistant password'
        text_body = (
            f"Hi {first_name},\n\n"
            f"You asked to reset the password for your ME Skin Assistant account.\n\n"
            f"Open this link to set a new password (expires in 1 hour):\n"
            f"{reset_url}\n\n"
            f"If you didn't request this, you can safely ignore this email — "
            f"your password won't change.\n\n"
            f"— The ME Skin Assistant team"
        )
        html_body = f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f4f4f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;line-height:1.55;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f4f4f7;padding:24px 0;">
  <tr><td align="center">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560"
           style="max-width:560px;background:#ffffff;border-radius:12px;
                  box-shadow:0 1px 3px rgba(0,0,0,0.06);overflow:hidden;">
      <tr><td style="padding:28px 32px 16px;">
        <p style="margin:0 0 6px;font-size:13px;letter-spacing:0.04em;
                  color:#6b7280;text-transform:uppercase;">ME Skin Assistant</p>
        <h1 style="margin:0;font-size:22px;font-weight:700;color:#111827;">
          Reset your password
        </h1>
      </td></tr>
      <tr><td style="padding:8px 32px 0;">
        <p style="margin:0 0 14px;font-size:15px;">Hi {first_name},</p>
        <p style="margin:0 0 14px;font-size:15px;">
          You asked to reset the password for your <strong>ME Skin Assistant</strong>
          account. Click the button below to choose a new one. This link expires in
          <strong>1 hour</strong>.
        </p>
      </td></tr>
      <tr><td align="center" style="padding:18px 32px 8px;">
        <a href="{reset_url}"
           style="display:inline-block;background:#4338ca;color:#ffffff;
                  text-decoration:none;padding:12px 28px;border-radius:8px;
                  font-weight:600;font-size:15px;">
          Reset password
        </a>
      </td></tr>
      <tr><td style="padding:8px 32px 4px;">
        <p style="margin:0 0 8px;font-size:13px;color:#6b7280;">
          If the button doesn't work, copy and paste this URL into your browser:
        </p>
        <p style="margin:0 0 14px;font-size:13px;word-break:break-all;">
          <a href="{reset_url}" style="color:#4338ca;">{reset_url}</a>
        </p>
      </td></tr>
      <tr><td style="padding:14px 32px 28px;border-top:1px solid #f3f4f6;">
        <p style="margin:0;font-size:13px;color:#6b7280;">
          If you didn't request this, you can safely ignore this email —
          your password won't change.
        </p>
      </td></tr>
    </table>
    <p style="margin:14px 0 0;font-size:12px;color:#9ca3af;">
      Sent because you requested a password reset on ME Skin Assistant.
    </p>
  </td></tr>
</table>
</body></html>"""

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
                reply_to=[settings.DEFAULT_FROM_EMAIL],
                headers={
                    # Tell Gmail this is a one-to-one transactional message.
                    'X-Entity-Ref-ID':           f'pw-reset-{uid}',
                    'X-Auto-Response-Suppress':  'All',
                    'Auto-Submitted':            'auto-generated',
                    'X-Mailer':                  'ME Skin Assistant',
                    'List-Unsubscribe':          f'<mailto:{settings.EMAIL_HOST_USER}?subject=Unsubscribe>',
                    'Precedence':                'transactional',
                },
            )
            msg.attach_alternative(html_body, 'text/html')
            msg.send(fail_silently=False)
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


# ---------------------------------------------------------------------------
# Role Management (Admin only)
# ---------------------------------------------------------------------------

class UserListView(APIView):
    """
    GET  /api/admin/users/          — list all users with their roles (admin only)
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.all().select_related('role', 'profile')
        data = []
        for u in users:
            data.append({
                'id':         u.id,
                'email':      u.email,
                'name':       f"{u.first_name} {u.last_name}".strip(),
                'role':       getattr(u, 'role', None) and u.role.role or 'user',
                'is_active':  u.is_active,
                'joined':     u.date_joined,
            })
        return Response(data)


class UserRoleView(APIView):
    """
    PATCH /api/admin/users/<id>/role/  — change a user's role (admin only)
    Body: { "role": "user" | "admin" | "dermatologist" | "salon" }
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    VALID_ROLES = {'user', 'admin'}

    def patch(self, request, pk):
        role = request.data.get('role', '').strip().lower()
        if role not in self.VALID_ROLES:
            return Response(
                {'error': f'Invalid role. Choose from: {", ".join(self.VALID_ROLES)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        user_role, _ = UserRole.objects.get_or_create(user=user)
        user_role.role = role
        user_role.save()

        logger.info("Role changed: user=%s role=%s by admin=%s", user.email, role, request.user.email)
        return Response({'message': f"Role updated to '{role}' for {user.email}."})


class MyRoleView(APIView):
    """GET /api/auth/my-role/  — return current user's role."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            role = request.user.role.role
        except Exception:
            role = 'user'
        return Response({'role': role})


class UpgradeAccountView(APIView):
    """POST /api/account/upgrade/  — process a premium subscription payment.

    Demo payment: the card details are validated and "charged" on the client;
    this endpoint receives the chosen plan + a card token (last4 only — full
    card numbers are NEVER sent to or stored on the server) and activates
    premium, returning a transaction reference like a real gateway would.
    """
    permission_classes = [IsAuthenticated]

    PLANS = {
        'monthly': {'amount': 4.99, 'label': 'Monthly'},
        'yearly':  {'amount': 39.99, 'label': 'Yearly'},
    }

    def post(self, request):
        import uuid
        from django.utils import timezone

        plan_key = (request.data or {}).get('plan', 'monthly')
        plan = self.PLANS.get(plan_key, self.PLANS['monthly'])
        card_last4 = str((request.data or {}).get('card_last4', '')).strip()[-4:]

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.account_type = 'premium'
        profile.save(update_fields=['account_type'])

        txn_id = f"ME-{uuid.uuid4().hex[:12].upper()}"
        logger.info("User %s upgraded to premium (plan=%s, amount=%.2f, txn=%s, card=****%s)",
                    request.user.email, plan_key, plan['amount'], txn_id, card_last4 or '----')

        return Response({
            'success': True,
            'account_type': 'premium',
            'transaction_id': txn_id,
            'plan': plan_key,
            'plan_label': plan['label'],
            'amount': plan['amount'],
            'currency': 'USD',
            'paid_at': timezone.now().isoformat(),
            'card_last4': card_last4,
        })


# ── Safepay payment gateway (cards + Easypaisa + JazzCash) ───────────
PREMIUM_PLANS_PKR = {
    'monthly': {'amount': 1400, 'label': 'Monthly'},
    'yearly':  {'amount': 11200, 'label': 'Yearly'},
}


class PaymentInitView(APIView):
    """POST /api/payments/init/  — create a Safepay hosted-checkout session.

    Returns a checkout_url the browser is redirected to, where the user picks
    Card / Easypaisa / JazzCash. Falls back to {configured: False} when Safepay
    keys are not set, so the frontend uses the built-in demo checkout instead.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from core import safepay
        from django.conf import settings

        if not safepay.is_configured():
            return Response({'configured': False}, status=status.HTTP_200_OK)

        plan_key = (request.data or {}).get('plan', 'monthly')
        plan = PREMIUM_PLANS_PKR.get(plan_key, PREMIUM_PLANS_PKR['monthly'])

        tracker = safepay.create_session(plan['amount'], currency='PKR')
        if not tracker:
            return Response({'error': 'Could not start payment. Try again.'},
                            status=status.HTTP_502_BAD_GATEWAY)

        front = settings.FRONTEND_BASE_URL.rstrip('/')
        url = safepay.checkout_url(
            tracker,
            redirect_url=f"{front}/upgrade?status=success",
            cancel_url=f"{front}/upgrade?status=cancelled",
            order_id=f"ME-{request.user.id}-{plan_key}",
        )
        return Response({
            'configured': True, 'checkout_url': url, 'tracker': tracker,
            'plan': plan_key, 'amount': plan['amount'], 'currency': 'PKR',
        })


class PaymentWebhookView(APIView):
    """POST /api/payments/webhook/  — Safepay calls this on payment events.

    Verifies the signature, and on a successful charge marks the matching user
    premium. This is the SOURCE OF TRUTH (we don't trust the browser redirect).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from core import safepay

        signature = request.headers.get('X-SFPY-SIGNATURE', '')
        if not safepay.verify_webhook(request.body, signature):
            return Response({'error': 'invalid signature'},
                            status=status.HTTP_400_BAD_REQUEST)

        payload = request.data or {}
        event = (payload.get('type') or payload.get('event') or '').lower()
        data = payload.get('data') or {}
        order_id = str(data.get('order_id') or data.get('metadata', {}).get('order_id') or '')

        if 'succeed' in event or 'paid' in event or 'complete' in event:
            # order_id format: ME-<user_id>-<plan>
            try:
                uid = int(order_id.split('-')[1])
                profile, _ = UserProfile.objects.get_or_create(user_id=uid)
                profile.account_type = 'premium'
                profile.save(update_fields=['account_type'])
                logger.info("Safepay webhook: user %s upgraded to premium (order=%s)", uid, order_id)
            except Exception as e:
                logger.error("Safepay webhook could not upgrade (order=%s): %s", order_id, e)
        return Response({'received': True})


class PaymentVerifyView(APIView):
    """POST /api/payments/verify/  — confirm a payment after the Safepay redirect.

    The browser returns to /upgrade?status=success&tracker=...; this queries
    Safepay directly for the tracker's payment state (authoritative) and
    activates premium when it reports paid."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from core import safepay

        tracker = (request.data or {}).get('tracker', '')
        if not tracker or not safepay.is_order_paid(tracker):
            return Response({'verified': False}, status=status.HTTP_400_BAD_REQUEST)

        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.account_type = 'premium'
        profile.save(update_fields=['account_type'])
        logger.info("User %s premium confirmed via Safepay tracker %s", request.user.email, tracker)
        return Response({'verified': True, 'account_type': 'premium'})
