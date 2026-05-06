"""
Tests for password reset flow:
  POST /api/auth/forgot-password/
  POST /api/auth/reset-password/
"""
import pytest
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='reset@fyp.com', email='reset@fyp.com',
        password='OldPass123!', first_name='Reset', last_name='User',
    )


@pytest.fixture
def reset_payload(user):
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return {'uid': uid, 'token': token}


@pytest.mark.django_db
class TestForgotPassword:

    def test_forgot_password_known_email(self, client, user):
        res = client.post('/api/auth/forgot-password/', {'email': user.email}, format='json')
        assert res.status_code == 200
        assert 'message' in res.data

    def test_forgot_password_unknown_email(self, client, db):
        """Should still return 200 to prevent user enumeration."""
        res = client.post('/api/auth/forgot-password/', {'email': 'nobody@fyp.com'}, format='json')
        assert res.status_code == 200

    def test_forgot_password_missing_email(self, client, db):
        res = client.post('/api/auth/forgot-password/', {}, format='json')
        assert res.status_code == 400


@pytest.mark.django_db
class TestResetPassword:

    def test_reset_password_success(self, client, user, reset_payload):
        res = client.post('/api/auth/reset-password/', {
            **reset_payload,
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.check_password('NewPass456!')

    def test_reset_password_mismatch(self, client, user, reset_payload):
        res = client.post('/api/auth/reset-password/', {
            **reset_payload,
            'new_password': 'NewPass456!',
            'confirm_password': 'WrongPass!',
        }, format='json')
        assert res.status_code == 400

    def test_reset_password_invalid_token(self, client, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        res = client.post('/api/auth/reset-password/', {
            'uid': uid,
            'token': 'invalid-token',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert res.status_code == 400

    def test_reset_password_invalid_uid(self, client, db):
        res = client.post('/api/auth/reset-password/', {
            'uid': 'baduid',
            'token': 'sometoken',
            'new_password': 'NewPass456!',
            'confirm_password': 'NewPass456!',
        }, format='json')
        assert res.status_code == 400

    def test_reset_password_token_used_twice(self, client, user, reset_payload):
        """Token should be invalid after first use."""
        payload = {**reset_payload, 'new_password': 'NewPass456!', 'confirm_password': 'NewPass456!'}
        client.post('/api/auth/reset-password/', payload, format='json')
        res = client.post('/api/auth/reset-password/', payload, format='json')
        assert res.status_code == 400
