"""
Tests for Product API endpoints.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.licenses.models import Activation, License, LicenseStatus


@pytest.mark.django_db
class TestActivationEndpoint:
    """Tests for license activation endpoint (US3)."""

    def test_activate_license(self, api_client, license):
        """Test activating a license."""
        response = api_client.post(
            '/api/v1/product/activate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug,
                'instance_id': 'https://newsite.com',
                'instance_name': 'New Site'
            },
            format='json'
        )
        
        assert response.status_code == 200
        data = response.json()['data']
        assert data['instance_id'] == 'https://newsite.com'
        assert data['is_valid'] is True
        assert 'activation_id' in data

    def test_activate_invalid_license_key(self, api_client, product):
        """Test activation with invalid license key fails."""
        response = api_client.post(
            '/api/v1/product/activate/',
            data={
                'license_key': 'invalid-key',
                'product_slug': product.slug,
                'instance_id': 'https://site.com'
            },
            format='json'
        )
        
        assert response.status_code == 404

    def test_activate_expired_license(self, api_client, license_key, product):
        """Test activation of expired license fails."""
        expired_license = License.objects.create(
            license_key=license_key,
            product=product,
            status=LicenseStatus.VALID,
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        response = api_client.post(
            '/api/v1/product/activate/',
            data={
                'license_key': license_key.key,
                'product_slug': product.slug,
                'instance_id': 'https://site.com'
            },
            format='json'
        )
        
        assert response.status_code == 400
        assert 'expired' in response.json()['error']['code']

    def test_activate_suspended_license(self, api_client, license):
        """Test activation of suspended license fails."""
        license.suspend()
        
        response = api_client.post(
            '/api/v1/product/activate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug,
                'instance_id': 'https://site.com'
            },
            format='json'
        )
        
        assert response.status_code == 400

    def test_activate_seat_limit_exceeded(self, api_client, license):
        """Test activation fails when seat limit exceeded."""
        # Fill up all seats
        for i in range(license.seat_limit):
            Activation.objects.create(
                license=license,
                instance_id=f'https://site{i}.com'
            )
        
        response = api_client.post(
            '/api/v1/product/activate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug,
                'instance_id': 'https://newsite.com'
            },
            format='json'
        )
        
        assert response.status_code == 400
        assert 'seat_limit' in response.json()['error']['code']

    def test_reactivate_same_instance(self, api_client, license, activation):
        """Test reactivating same instance succeeds."""
        response = api_client.post(
            '/api/v1/product/activate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug,
                'instance_id': activation.instance_id
            },
            format='json'
        )
        
        assert response.status_code == 200


@pytest.mark.django_db
class TestValidationEndpoint:
    """Tests for license validation endpoint (US4)."""

    def test_validate_license(self, api_client, license):
        """Test validating a license."""
        response = api_client.post(
            '/api/v1/product/validate/',
            data={
                'license_key': license.license_key.key
            },
            format='json'
        )
        
        assert response.status_code == 200
        data = response.json()['data']
        assert data['is_valid'] is True
        assert len(data['licenses']) >= 1

    def test_validate_with_product_filter(self, api_client, license):
        """Test validating license for specific product."""
        response = api_client.post(
            '/api/v1/product/validate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug
            },
            format='json'
        )
        
        assert response.status_code == 200
        data = response.json()['data']
        assert len(data['licenses']) == 1
        assert data['licenses'][0]['product']['slug'] == license.product.slug

    def test_validate_invalid_key(self, api_client):
        """Test validation with invalid key fails."""
        response = api_client.post(
            '/api/v1/product/validate/',
            data={'license_key': 'invalid-key'},
            format='json'
        )
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestDeactivationEndpoint:
    """Tests for license deactivation endpoint (US5)."""

    def test_deactivate_license(self, api_client, license, activation):
        """Test deactivating a license."""
        response = api_client.post(
            '/api/v1/product/deactivate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug,
                'instance_id': activation.instance_id
            },
            format='json'
        )
        
        assert response.status_code == 200
        activation.refresh_from_db()
        assert activation.is_active is False

    def test_deactivate_nonexistent_activation(self, api_client, license):
        """Test deactivating non-existent activation fails."""
        response = api_client.post(
            '/api/v1/product/deactivate/',
            data={
                'license_key': license.license_key.key,
                'product_slug': license.product.slug,
                'instance_id': 'https://nonexistent.com'
            },
            format='json'
        )
        
        assert response.status_code == 404


@pytest.mark.django_db
class TestStatusEndpoint:
    """Tests for license status endpoint."""

    def test_get_license_status(self, api_client, license, activation):
        """Test getting license status."""
        response = api_client.get(
            '/api/v1/product/status/',
            {'license_key': license.license_key.key}
        )
        
        assert response.status_code == 200
        data = response.json()['data']
        assert data['license_key'] == license.license_key.key
        assert len(data['licenses']) >= 1
        assert len(data['activations']) >= 1

    def test_get_status_missing_key(self, api_client):
        """Test status without license key fails."""
        response = api_client.get('/api/v1/product/status/')
        
        assert response.status_code == 400
