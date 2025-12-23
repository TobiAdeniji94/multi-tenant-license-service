"""
Pytest configuration and fixtures.
"""
from datetime import timedelta

from django.utils import timezone

import pytest


@pytest.fixture
def api_client():
    """Return a DRF API client."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def brand(db):
    """Create a test brand."""
    from apps.brands.models import Brand

    return Brand.objects.create(name="Test Brand", slug="test-brand")


@pytest.fixture
def product(db, brand):
    """Create a test product."""
    from apps.brands.models import Product

    return Product.objects.create(
        brand=brand, name="Test Product", slug="test-product", default_seat_limit=3
    )


@pytest.fixture
def license_key(db, brand):
    """Create a test license key."""
    from apps.licenses.models import LicenseKey

    return LicenseKey.objects.create(
        brand=brand, customer_email="test@example.com", customer_name="Test User"
    )


@pytest.fixture
def license(db, license_key, product):
    """Create a test license."""
    from apps.licenses.models import License, LicenseStatus

    return License.objects.create(
        license_key=license_key,
        product=product,
        status=LicenseStatus.VALID,
        expires_at=timezone.now() + timedelta(days=365),
        seat_limit=3,
    )


@pytest.fixture
def activation(db, license):
    """Create a test activation."""
    from apps.licenses.models import Activation

    return Activation.objects.create(
        license=license, instance_id="https://example.com", instance_name="Example Site"
    )


@pytest.fixture
def brand_auth_headers(brand):
    """Return authentication headers for brand API."""
    return {
        "HTTP_X_API_KEY": brand.api_key,
        "HTTP_X_API_SECRET": brand.api_secret,
    }
