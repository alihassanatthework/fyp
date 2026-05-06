"""
Tests for authentication endpoints:
  POST /api/auth/register/
  POST /api/auth/login/
  POST /api/auth/logout/
  GET  /api/auth/me/
  POST /api/auth/change-password/
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def registered_user(db):
    """Create a real user in the test DB and return (user, password)."""
    user = User.objects.create_user(
        username='test@fyp.com',
        email='test@fyp.com',
        password='TestPass123!',
        first_name='Test',
        last_name='User',
    )
    return user, 'TestPass123!'


@pytest.fixture
def auth_client(client, registered_user):
    """APIClient with a valid JWT already attached."""
    user, _ = registered_user
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client, user, str(refresh)


# ── register ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegister:
    URL = '/api/auth/register/'

    def test_register_success(self, client):
        res = client.post(self.URL, {
            'full_name': 'Ali Hassan',
            'email': 'ali@fyp.com',
            'password': 'StrongPass99!',
            'confirm_password': 'StrongPass99!',
            'health_conditions': [],
        }, format='json')
        assert res.status_code == 201
        assert 'access' in res.data
        assert 'refresh' in res.data
        assert res.data['user']['email'] == 'ali@fyp.com'
        assert User.objects.filter(email='ali@fyp.com').exists()

    def test_register_duplicate_email(self, client, registered_user):
        res = client.post(self.URL, {
            'full_name': 'Another User',
            'email': 'test@fyp.com',
            'password': 'StrongPass99!',
            'confirm_password': 'StrongPass99!',
        }, format='json')
        assert res.status_code == 400

    def test_register_password_mismatch(self, client):
        res = client.post(self.URL, {
            'full_name': 'User',
            'email': 'new@fyp.com',
            'password': 'StrongPass99!',
            'confirm_password': 'WrongPass!',
        }, format='json')
        assert res.status_code == 400

    def test_register_missing_fields(self, client):
        res = client.post(self.URL, {'email': 'x@fyp.com'}, format='json')
        assert res.status_code == 400

    def test_register_creates_profile_and_medical_history(self, client):
        res = client.post(self.URL, {
            'full_name': 'Jane Doe',
            'email': 'jane@fyp.com',
            'password': 'StrongPass99!',
            'confirm_password': 'StrongPass99!',
            'health_conditions': ['Allergies', 'Diabetes'],
        }, format='json')
        assert res.status_code == 201
        user = User.objects.get(email='jane@fyp.com')
        assert hasattr(user, 'profile')
        assert hasattr(user, 'medical_history')
        assert user.medical_history.has_allergies is True
        assert user.medical_history.is_diabetic is True


# ── login ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:
    URL = '/api/auth/login/'

    def test_login_success(self, client, registered_user):
        user, password = registered_user
        res = client.post(self.URL, {'email': user.email, 'password': password}, format='json')
        assert res.status_code == 200
        assert 'access' in res.data
        assert 'refresh' in res.data

    def test_login_wrong_password(self, client, registered_user):
        user, _ = registered_user
        res = client.post(self.URL, {'email': user.email, 'password': 'wrongpass'}, format='json')
        assert res.status_code == 401

    def test_login_unknown_email(self, client):
        res = client.post(self.URL, {'email': 'nobody@fyp.com', 'password': 'pass'}, format='json')
        assert res.status_code == 401

    def test_login_missing_fields(self, client):
        res = client.post(self.URL, {}, format='json')
        assert res.status_code == 400


# ── me ───────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestMe:
    URL = '/api/auth/me/'

    def test_me_authenticated(self, auth_client):
        client, user, _ = auth_client
        res = client.get(self.URL)
        assert res.status_code == 200
        assert res.data['user']['email'] == user.email

    def test_me_unauthenticated(self, client):
        res = client.get(self.URL)
        assert res.status_code == 401


# ── change password ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:
    URL = '/api/auth/change-password/'

    def test_change_password_success(self, auth_client):
        client, user, _ = auth_client
        res = client.post(self.URL, {
            'old_password':     'TestPass123!',
            'new_password':     'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewPass456!')

    def test_change_password_wrong_old(self, auth_client):
        client, _, _ = auth_client
        res = client.post(self.URL, {
            'old_password':     'wrongold',
            'new_password':     'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert res.status_code == 400

    def test_change_password_mismatch(self, auth_client):
        client, _, _ = auth_client
        res = client.post(self.URL, {
            'old_password':     'TestPass123!',
            'new_password':     'NewPass456!',
            'confirm_password': 'Different456!',
        }, format='json')
        assert res.status_code == 400

    def test_change_password_unauthenticated(self, client):
        res = client.post(self.URL, {
            'old_password': 'x', 'new_password': 'y', 'confirm_password': 'y'
        }, format='json')
        assert res.status_code == 401
