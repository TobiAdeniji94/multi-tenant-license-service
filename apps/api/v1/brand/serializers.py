"""
Serializers for Brand API.
"""
from datetime import timedelta

from django.utils import timezone

from rest_framework import serializers

from apps.brands.models import Product
from apps.licenses.models import Activation, License, LicenseKey, LicenseStatus


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "default_seat_limit",
            "is_active",
        ]
        read_only_fields = ["id"]


class ActivationSerializer(serializers.ModelSerializer):
    """Serializer for Activation model."""

    class Meta:
        model = Activation
        fields = [
            "id",
            "instance_id",
            "instance_name",
            "is_active",
            "activated_at",
            "last_check_at",
        ]
        read_only_fields = ["id", "activated_at", "last_check_at"]


class LicenseSerializer(serializers.ModelSerializer):
    """Serializer for License model."""

    product = ProductSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    seats_used = serializers.IntegerField(read_only=True)
    seats_available = serializers.IntegerField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    activations = ActivationSerializer(many=True, read_only=True)

    class Meta:
        model = License
        fields = [
            "id",
            "product",
            "product_id",
            "status",
            "expires_at",
            "seat_limit",
            "seats_used",
            "seats_available",
            "is_valid",
            "activations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LicenseCreateSerializer(serializers.Serializer):
    """Serializer for creating a new license."""

    product_id = serializers.UUIDField()
    expires_at = serializers.DateTimeField(required=False)
    seat_limit = serializers.IntegerField(required=False, min_value=0)

    def validate_product_id(self, value):
        """Validate that product exists and belongs to the brand."""
        brand = self.context.get("brand")
        if not Product.objects.filter(id=value, brand=brand, is_active=True).exists():
            raise serializers.ValidationError("Product not found or not active")
        return value

    def create(self, validated_data):
        license_key = self.context["license_key"]
        product = Product.objects.get(id=validated_data["product_id"])

        # Default expiration: 1 year from now
        expires_at = validated_data.get(
            "expires_at", timezone.now() + timedelta(days=365)
        )

        # Default seat limit from product
        seat_limit = validated_data.get("seat_limit", product.default_seat_limit)

        license = License.objects.create(
            license_key=license_key,
            product=product,
            expires_at=expires_at,
            seat_limit=seat_limit,
            status=LicenseStatus.VALID,
        )
        return license


class LicenseKeySerializer(serializers.ModelSerializer):
    """Serializer for LicenseKey model."""

    licenses = LicenseSerializer(many=True, read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True)

    class Meta:
        model = LicenseKey
        fields = [
            "id",
            "key",
            "customer_email",
            "customer_name",
            "brand_name",
            "licenses",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "key", "created_at", "updated_at"]


class LicenseKeyCreateSerializer(serializers.Serializer):
    """Serializer for creating a new license key."""

    customer_email = serializers.EmailField()
    customer_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def create(self, validated_data):
        brand = self.context["brand"]
        license_key = LicenseKey.objects.create(
            brand=brand,
            customer_email=validated_data["customer_email"],
            customer_name=validated_data.get("customer_name", ""),
        )
        return license_key


class LicenseRenewSerializer(serializers.Serializer):
    """Serializer for renewing a license."""

    days = serializers.IntegerField(default=365, min_value=1, max_value=3650)


class CustomerLicenseQuerySerializer(serializers.Serializer):
    """Serializer for customer license query parameters."""

    email = serializers.EmailField()


class CustomerLicenseResponseSerializer(serializers.Serializer):
    """Serializer for customer license response."""

    email = serializers.EmailField()
    license_keys = LicenseKeySerializer(many=True)
    total_licenses = serializers.IntegerField()
