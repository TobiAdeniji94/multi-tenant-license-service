"""
Tests for Brand API endpoints.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.licenses.models import License, LicenseKey, LicenseStatus


@pytest.mark.django_db
class TestLicenseKeyEndpoints:
    """Tests for license key management endpoints."""

    def test_create_license_key(self, api_client, brand, brand_auth_headers):
        """Test creating a new license key."""
        response = api_client.post(
            '/api/v1/brand/license-keys/',
            data={
                'customer_email': 'newuser@example.com',
                'customer_name': 'New User'
            },
            format='json',
            **brand_auth_headers
        )
        
        assert response.status_code == 201
        assert 'data' in response.json()
        assert response.json()['data']['customer_email'] == 'newuser@example.com'
        assert 'key' in response.json()['data']

    def test_create_license_key_without_auth(self, api_client):
        """Test creating license key without authentication fails."""
        response = api_client.post(
            '/api/v1/brand/license-keys/',
            data={'customer_email': 'test@example.com'},
            format='json'
        )
        
        assert response.status_code == 401

    def test_list_license_keys(self, api_client, license_key, brand_auth_headers):
        """Test listing license keys."""
        response = api_client.get(
            '/api/v1/brand/license-keys/',
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        assert 'data' in response.json()
        assert len(response.json()['data']) >= 1

    def test_get_license_key_detail(self, api_client, license_key, brand_auth_headers):
        """Test getting license key details."""
        response = api_client.get(
            f'/api/v1/brand/license-keys/{license_key.key}/',
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()['data']['key'] == license_key.key


@pytest.mark.django_db
class TestLicenseEndpoints:
    """Tests for license management endpoints."""

    def test_create_license(self, api_client, license_key, product, brand_auth_headers):
        """Test creating a new license."""
        response = api_client.post(
            f'/api/v1/brand/license-keys/{license_key.key}/licenses/',
            data={
                'product_id': str(product.id),
                'seat_limit': 5
            },
            format='json',
            **brand_auth_headers
        )
        
        assert response.status_code == 201
        assert response.json()['data']['seat_limit'] == 5
        assert response.json()['data']['status'] == 'valid'

    def test_create_license_invalid_product(self, api_client, license_key, brand_auth_headers):
        """Test creating license with invalid product fails."""
        response = api_client.post(
            f'/api/v1/brand/license-keys/{license_key.key}/licenses/',
            data={
                'product_id': '00000000-0000-0000-0000-000000000000'
            },
            format='json',
            **brand_auth_headers
        )
        
        assert response.status_code == 400

    def test_renew_license(self, api_client, license, brand_auth_headers):
        """Test renewing a license."""
        old_expiry = license.expires_at
        
        response = api_client.post(
            f'/api/v1/brand/licenses/{license.id}/renew/',
            data={'days': 30},
            format='json',
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        license.refresh_from_db()
        assert license.expires_at > old_expiry

    def test_suspend_license(self, api_client, license, brand_auth_headers):
        """Test suspending a license."""
        response = api_client.post(
            f'/api/v1/brand/licenses/{license.id}/suspend/',
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        license.refresh_from_db()
        assert license.status == LicenseStatus.SUSPENDED

    def test_resume_license(self, api_client, license, brand_auth_headers):
        """Test resuming a suspended license."""
        license.suspend()
        
        response = api_client.post(
            f'/api/v1/brand/licenses/{license.id}/resume/',
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        license.refresh_from_db()
        assert license.status == LicenseStatus.VALID

    def test_cancel_license(self, api_client, license, brand_auth_headers):
        """Test cancelling a license."""
        response = api_client.post(
            f'/api/v1/brand/licenses/{license.id}/cancel/',
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        license.refresh_from_db()
        assert license.status == LicenseStatus.CANCELLED


@pytest.mark.django_db
class TestCustomerLookup:
    """Tests for customer license lookup (US6)."""

    def test_lookup_customer_licenses(self, api_client, license, brand_auth_headers):
        """Test looking up licenses by customer email."""
        response = api_client.get(
            '/api/v1/brand/customers/',
            {'email': license.license_key.customer_email},
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()['data']
        assert data['email'] == license.license_key.customer_email
        assert data['total_licenses'] >= 1

    def test_lookup_nonexistent_customer(self, api_client, brand_auth_headers):
        """Test looking up non-existent customer returns empty."""
        response = api_client.get(
            '/api/v1/brand/customers/',
            {'email': 'nobody@example.com'},
            **brand_auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()['data']['total_licenses'] == 0
