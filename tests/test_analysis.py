"""
Tests for analysis endpoints:
  GET  /api/analysis/history/
  GET  /api/analysis/stats/
  GET  /api/analysis/<id>/
  DELETE /api/analysis/<id>/
"""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from image_analysis.models import AnalysisResult


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='scan@fyp.com', email='scan@fyp.com', password='Pass123!'
    )


@pytest.fixture
def auth_client(client, user):
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    return client


@pytest.fixture
def analysis(user):
    return AnalysisResult.objects.create(
        user=user,
        analysis_id='TEST0001',
        analysis_type='skin',
        severity_label='Mild',
        max_severity=20,
        conditions=[{'name': 'Acne', 'severity_score': 20, 'severity_level': 'Mild'}],
        recommendations=['Use gentle cleanser'],
        recommendations_structured={},
    )


# ── history ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnalysisHistory:
    URL = '/api/analysis/history/'

    def test_history_empty(self, auth_client):
        res = auth_client.get(self.URL)
        assert res.status_code == 200
        assert res.data['results'] == []

    def test_history_returns_user_records(self, auth_client, analysis):
        res = auth_client.get(self.URL)
        assert res.status_code == 200
        assert res.data['count'] == 1
        assert res.data['results'][0]['id'] == 'TEST0001'

    def test_history_filter_by_type(self, auth_client, user):
        AnalysisResult.objects.create(
            user=user, analysis_id='SKIN01', analysis_type='skin',
            severity_label='Mild', max_severity=10,
        )
        AnalysisResult.objects.create(
            user=user, analysis_id='SCALP01', analysis_type='scalp',
            severity_label='Moderate', max_severity=50,
        )
        res = auth_client.get(self.URL + '?type=Skin Scan')
        assert res.status_code == 200
        ids = [r['id'] for r in res.data['results']]
        assert 'SKIN01' in ids
        assert 'SCALP01' not in ids

    def test_history_isolated_per_user(self, client, db):
        """User A cannot see User B's analyses."""
        user_b = User.objects.create_user(username='b@fyp.com', email='b@fyp.com', password='Pass!')
        AnalysisResult.objects.create(
            user=user_b, analysis_id='USERB01', analysis_type='skin',
            severity_label='Mild', max_severity=10,
        )
        user_a = User.objects.create_user(username='a@fyp.com', email='a@fyp.com', password='Pass!')
        token = str(RefreshToken.for_user(user_a).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        res = client.get(self.URL)
        assert res.status_code == 200
        assert res.data['count'] == 0

    def test_history_unauthenticated(self, client):
        res = client.get(self.URL)
        assert res.status_code == 401


# ── stats ─────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnalysisStats:
    URL = '/api/analysis/stats/'

    def test_stats_empty(self, auth_client):
        res = auth_client.get(self.URL)
        assert res.status_code == 200
        assert res.data['total_scans'] == 0

    def test_stats_correct_counts(self, auth_client, user):
        AnalysisResult.objects.create(user=user, analysis_id='S1', analysis_type='skin',  severity_label='Mild',     max_severity=20)
        AnalysisResult.objects.create(user=user, analysis_id='S2', analysis_type='scalp', severity_label='Moderate', max_severity=60)
        AnalysisResult.objects.create(user=user, analysis_id='S3', analysis_type='skin',  severity_label='Severe',   max_severity=85)
        res = auth_client.get(self.URL)
        assert res.data['total_scans']  == 3
        assert res.data['skin_scans']   == 2
        assert res.data['scalp_scans']  == 1
        assert res.data['severity_counts']['Mild']     == 1
        assert res.data['severity_counts']['Moderate'] == 1
        assert res.data['severity_counts']['Severe']   == 1


# ── detail & delete ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAnalysisDetail:

    def test_get_own_analysis(self, auth_client, analysis):
        res = auth_client.get(f'/api/analysis/{analysis.analysis_id}/')
        assert res.status_code == 200
        assert res.data['analysis_id'] == analysis.analysis_id

    def test_cannot_get_other_users_analysis(self, client, db):
        owner = User.objects.create_user(username='owner@fyp.com', email='owner@fyp.com', password='P!')
        other = User.objects.create_user(username='other@fyp.com', email='other@fyp.com', password='P!')
        ar = AnalysisResult.objects.create(
            user=owner, analysis_id='OWN01', analysis_type='skin',
            severity_label='Mild', max_severity=10,
        )
        token = str(RefreshToken.for_user(other).access_token)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        res = client.get(f'/api/analysis/{ar.analysis_id}/')
        assert res.status_code == 404

    def test_delete_analysis(self, auth_client, analysis):
        res = auth_client.delete(f'/api/analysis/{analysis.analysis_id}/')
        assert res.status_code == 200
        assert not AnalysisResult.objects.filter(analysis_id=analysis.analysis_id).exists()

    def test_get_nonexistent(self, auth_client):
        res = auth_client.get('/api/analysis/DOESNOTEXIST/')
        assert res.status_code == 404
