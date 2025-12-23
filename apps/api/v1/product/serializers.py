"""
Serializers for Product API.
"""
from rest_framework import serializers


class ProductInfoSerializer(serializers.Serializer):
    """Minimal product info for product API responses."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class LicenseInfoSerializer(serializers.Serializer):
    """License info for product API responses."""

    id = serializers.UUIDField()
    product = ProductInfoSerializer()
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()
    is_valid = serializers.BooleanField()
    seat_limit = serializers.IntegerField()
    seats_used = serializers.IntegerField()
    seats_available = serializers.IntegerField(allow_null=True)


class ActivationInfoSerializer(serializers.Serializer):
    """Activation info for product API responses."""

    id = serializers.UUIDField()
    instance_id = serializers.CharField()
    instance_name = serializers.CharField()
    is_active = serializers.BooleanField()
    activated_at = serializers.DateTimeField()


class ActivateLicenseSerializer(serializers.Serializer):
    """Serializer for license activation request."""

    license_key = serializers.CharField()
    product_slug = serializers.CharField()
    instance_id = serializers.CharField(max_length=255)
    instance_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    instance_metadata = serializers.JSONField(required=False, default=dict)


class ActivationResponseSerializer(serializers.Serializer):
    """Serializer for activation response."""

    activation_id = serializers.UUIDField()
    license_id = serializers.UUIDField()
    product = ProductInfoSerializer()
    instance_id = serializers.CharField()
    is_valid = serializers.BooleanField()
    expires_at = serializers.DateTimeField()
    seats_used = serializers.IntegerField()
    seats_available = serializers.IntegerField(allow_null=True)


class ValidateLicenseSerializer(serializers.Serializer):
    """Serializer for license validation request."""

    license_key = serializers.CharField()
    product_slug = serializers.CharField(required=False)
    instance_id = serializers.CharField(max_length=255, required=False)


class ValidationResponseSerializer(serializers.Serializer):
    """Serializer for validation response."""

    is_valid = serializers.BooleanField()
    license_key = serializers.CharField()
    licenses = LicenseInfoSerializer(many=True)
    message = serializers.CharField(required=False)


class DeactivateLicenseSerializer(serializers.Serializer):
    """Serializer for license deactivation request."""

    license_key = serializers.CharField()
    product_slug = serializers.CharField()
    instance_id = serializers.CharField(max_length=255)


class LicenseStatusResponseSerializer(serializers.Serializer):
    """Serializer for license status response."""

    license_key = serializers.CharField()
    customer_email = serializers.EmailField()
    brand = serializers.CharField()
    licenses = LicenseInfoSerializer(many=True)
    activations = ActivationInfoSerializer(many=True)
