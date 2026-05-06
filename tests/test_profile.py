"""
Tests for profile endpoints:
  GET   /api/profile/
  PATCH /api/profile/
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import UserProfile, MedicalHistory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    u = User.objects.create_user(
        username='profile@fyp.com', email='profile@fyp.com',
        password='Pass123!', first_name='Ali', last_name='Hassan',
    )
    UserProfile.objects.create(user=u)
    MedicalHistory.objects.create(user=u)
    return u


@pytest.fixture
def auth_client(client, user):
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return client


@pytest.mark.django_db
class TestProfile:

    def test_get_profile(self, auth_client, user):
        res = auth_client.get('/api/profile/')
        assert res.status_code == 200
        assert res.data['user']['email'] == user.email
        assert 'profile' in res.data
        assert 'medical_history' in res.data

    def test_update_name(self, auth_client, user):
        res = auth_client.patch('/api/profile/', {
            'user': {'first_name': 'Updated', 'last_name': 'Name'}
        }, format='json')
        assert res.status_code == 200
        user.refresh_from_db()
        assert user.first_name == 'Updated'

    def test_update_skin_type(self, auth_client, user):
        res = auth_client.patch('/api/profile/', {
            'profile': {'skin_type': 'oily'}
        }, format='json')
        assert res.status_code == 200
        user.profile.refresh_from_db()
        assert user.profile.skin_type == 'oily'

    def test_update_medical_history(self, auth_client, user):
        res = auth_client.patch('/api/profile/', {
            'medical_history': {'has_allergies': True, 'is_diabetic': True}
        }, format='json')
        assert res.status_code == 200
        user.medical_history.refresh_from_db()
        assert user.medical_history.has_allergies is True
        assert user.medical_history.is_diabetic is True

    def test_profile_unauthenticated(self, client):
        res = client.get('/api/profile/')
        assert res.status_code == 401
