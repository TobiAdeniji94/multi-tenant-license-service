"""
Tests for models.
"""
import pytest
from datetime import timedelta
from django.utils import timezone

from apps.brands.models import Brand, Product
from apps.licenses.models import Activation, License, LicenseKey, LicenseStatus


@pytest.mark.django_db
class TestBrandModel:
    """Tests for Brand model."""

    def test_brand_creation(self):
        """Test brand is created with API credentials."""
        brand = Brand.objects.create(name='WP Rocket', slug='wp-rocket')
        
        assert brand.name == 'WP Rocket'
        assert brand.slug == 'wp-rocket'
        assert brand.api_key is not None
        assert brand.api_secret is not None
        assert len(brand.api_key) == 64
        assert len(brand.api_secret) == 128

    def test_brand_regenerate_credentials(self):
        """Test API credentials can be regenerated."""
        brand = Brand.objects.create(name='Test', slug='test')
        old_key = brand.api_key
        old_secret = brand.api_secret
        
        brand.regenerate_credentials()
        
        assert brand.api_key != old_key
        assert brand.api_secret != old_secret


@pytest.mark.django_db
class TestProductModel:
    """Tests for Product model."""

    def test_product_creation(self, brand):
        """Test product creation."""
        product = Product.objects.create(
            brand=brand,
            name='Pro Plan',
            slug='pro-plan',
            default_seat_limit=5
        )
        
        assert product.brand == brand
        assert product.name == 'Pro Plan'
        assert product.default_seat_limit == 5


@pytest.mark.django_db
class TestLicenseKeyModel:
    """Tests for LicenseKey model."""

    def test_license_key_generation(self, brand):
        """Test license key is auto-generated."""
        license_key = LicenseKey.objects.create(
            brand=brand,
            customer_email='user@example.com'
        )
        
        assert license_key.key is not None
        assert len(license_key.key) > 20

    def test_license_key_unique(self, brand):
        """Test license keys are unique."""
        lk1 = LicenseKey.objects.create(brand=brand, customer_email='a@example.com')
        lk2 = LicenseKey.objects.create(brand=brand, customer_email='b@example.com')
        
        assert lk1.key != lk2.key


@pytest.mark.django_db
class TestLicenseModel:
    """Tests for License model."""

    def test_license_is_valid(self, license):
        """Test license validity check."""
        assert license.is_valid is True

    def test_license_expired(self, license_key, product):
        """Test expired license is not valid."""
        expired_license = License.objects.create(
            license_key=license_key,
            product=product,
            status=LicenseStatus.VALID,
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        assert expired_license.is_valid is False

    def test_license_suspended_not_valid(self, license):
        """Test suspended license is not valid."""
        license.suspend()
        assert license.is_valid is False
        assert license.status == LicenseStatus.SUSPENDED

    def test_license_resume(self, license):
        """Test resuming a suspended license."""
        license.suspend()
        license.resume()
        assert license.status == LicenseStatus.VALID

    def test_license_cancel(self, license):
        """Test cancelling a license."""
        license.cancel()
        assert license.status == LicenseStatus.CANCELLED
        assert license.is_valid is False

    def test_license_renew(self, license):
        """Test renewing a license."""
        old_expiry = license.expires_at
        license.renew(days=30)
        assert license.expires_at > old_expiry

    def test_seat_management(self, license):
        """Test seat counting."""
        assert license.seats_used == 0
        assert license.seats_available == 3
        assert license.can_activate() is True

        # Create activations
        Activation.objects.create(license=license, instance_id='site1.com')
        Activation.objects.create(license=license, instance_id='site2.com')
        
        assert license.seats_used == 2
        assert license.seats_available == 1
        assert license.can_activate() is True

        Activation.objects.create(license=license, instance_id='site3.com')
        
        assert license.seats_used == 3
        assert license.seats_available == 0
        assert license.can_activate() is False


@pytest.mark.django_db
class TestActivationModel:
    """Tests for Activation model."""

    def test_activation_creation(self, license):
        """Test activation creation."""
        activation = Activation.objects.create(
            license=license,
            instance_id='https://mysite.com',
            instance_name='My Site'
        )
        
        assert activation.is_active is True
        assert activation.instance_id == 'https://mysite.com'

    def test_activation_deactivate(self, activation):
        """Test deactivating an activation."""
        activation.deactivate()
        
        assert activation.is_active is False
        assert activation.deactivated_at is not None
