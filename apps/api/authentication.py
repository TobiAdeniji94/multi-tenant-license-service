"""
Custom authentication classes for Brand and Product APIs.
"""
import logging

from rest_framework import authentication, exceptions

from apps.brands.models import Brand
from apps.licenses.models import LicenseKey

logger = logging.getLogger(__name__)


class BrandAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Authentication for brand systems using API key and secret.

    Expects headers:
        X-API-Key: <brand_api_key>
        X-API-Secret: <brand_api_secret>
    """

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_API_KEY")
        api_secret = request.META.get("HTTP_X_API_SECRET")

        if not api_key or not api_secret:
            return None  # No credentials provided, skip this auth

        try:
            brand = Brand.objects.get(api_key=api_key, is_active=True)
        except Brand.DoesNotExist:
            logger.warning("Brand authentication failed: invalid API key")
            raise exceptions.AuthenticationFailed("Invalid API credentials")

        # Verify secret
        if brand.api_secret != api_secret:
            logger.warning(
                f"Brand authentication failed: invalid secret for brand {brand.slug}"
            )
            raise exceptions.AuthenticationFailed("Invalid API credentials")

        logger.debug(f"Brand authenticated: {brand.slug}")

        # Return (user, auth) tuple - we use brand as the "user"
        return (brand, None)

    def authenticate_header(self, request):
        return "API-Key"


class LicenseKeyAuthentication(authentication.BaseAuthentication):
    """
    Authentication for end-user products using license key.

    Expects header:
        X-License-Key: <license_key>

    Or query parameter:
        ?license_key=<license_key>
    """

    def authenticate(self, request):
        # Try header first
        license_key = request.META.get("HTTP_X_LICENSE_KEY")

        # Fall back to query parameter
        if not license_key:
            license_key = request.query_params.get("license_key")

        # Also check request body for POST requests
        if not license_key and request.method == "POST":
            license_key = request.data.get("license_key")

        if not license_key:
            return None  # No credentials provided, skip this auth

        try:
            license_key_obj = LicenseKey.objects.select_related("brand").get(
                key=license_key, is_active=True
            )
        except LicenseKey.DoesNotExist:
            logger.warning("License key authentication failed: invalid key")
            raise exceptions.AuthenticationFailed("Invalid license key")

        logger.debug(f"License key authenticated: {license_key_obj.key[:8]}...")

        # Return (user, auth) tuple - we use license_key as the "user"
        return (license_key_obj, None)

    def authenticate_header(self, request):
        return "License-Key"
