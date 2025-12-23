"""
Product API views for license activation and validation.
"""
import logging

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.api.exceptions import (
    ActivationNotFoundError,
    LicenseExpiredError,
    LicenseInvalidError,
    LicenseKeyNotFoundError,
    LicenseNotFoundError,
    SeatLimitExceededError,
)
from apps.licenses.models import Activation, License, LicenseKey, LicenseStatus

from .serializers import (
    ActivateLicenseSerializer,
    ActivationResponseSerializer,
    DeactivateLicenseSerializer,
    LicenseStatusResponseSerializer,
    ValidateLicenseSerializer,
    ValidationResponseSerializer,
)

logger = logging.getLogger(__name__)


class ActivateLicenseView(APIView):
    """
    Activate a license for a specific instance.
    US3: End-user product can activate a license.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Product API"],
        summary="Activate license",
        description="Activate a license for a specific instance (site URL, machine ID, etc.)",
        request=ActivateLicenseSerializer,
        responses={200: ActivationResponseSerializer},
    )
    @transaction.atomic
    def post(self, request):
        serializer = ActivateLicenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Find the license key
        try:
            license_key = LicenseKey.objects.select_related("brand").get(
                key=data["license_key"], is_active=True
            )
        except LicenseKey.DoesNotExist:
            raise LicenseKeyNotFoundError()

        # Find the license for the specified product
        try:
            license = License.objects.select_related("product").get(
                license_key=license_key,
                product__slug=data["product_slug"],
                product__is_active=True,
            )
        except License.DoesNotExist:
            raise LicenseNotFoundError(
                detail=f"No license found for product '{data['product_slug']}'"
            )

        # Check license validity
        if license.status != LicenseStatus.VALID:
            raise LicenseInvalidError(detail=f"License is {license.status}")

        if license.expires_at < timezone.now():
            raise LicenseExpiredError()

        # Check for existing activation
        existing_activation = Activation.objects.filter(
            license=license, instance_id=data["instance_id"]
        ).first()

        if existing_activation:
            if existing_activation.is_active:
                # Already activated, just update last check
                existing_activation.record_check()
                logger.info(
                    f"License re-activated: {license.id} on {data['instance_id']}"
                )
            else:
                # Reactivate
                if not license.can_activate():
                    raise SeatLimitExceededError(
                        detail=f"Seat limit ({license.seat_limit}) exceeded"
                    )
                existing_activation.is_active = True
                existing_activation.deactivated_at = None
                existing_activation.save()
                logger.info(
                    f"License reactivated: {license.id} on {data['instance_id']}"
                )

            activation = existing_activation
        else:
            # New activation - check seat limit
            if not license.can_activate():
                raise SeatLimitExceededError(
                    detail=f"Seat limit ({license.seat_limit}) exceeded. "
                    f"{license.seats_used}/{license.seat_limit} seats used."
                )

            # Create activation
            activation = Activation.objects.create(
                license=license,
                instance_id=data["instance_id"],
                instance_name=data.get("instance_name", ""),
                instance_metadata=data.get("instance_metadata", {}),
            )
            logger.info(f"License activated: {license.id} on {data['instance_id']}")

        # Build response
        response_data = {
            "activation_id": activation.id,
            "license_id": license.id,
            "product": {
                "id": license.product.id,
                "name": license.product.name,
                "slug": license.product.slug,
            },
            "instance_id": activation.instance_id,
            "is_valid": license.is_valid,
            "expires_at": license.expires_at,
            "seats_used": license.seats_used,
            "seats_available": license.seats_available,
        }

        return Response({"data": response_data})


class ValidateLicenseView(APIView):
    """
    Validate a license key.
    US4: User can check license status.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Product API"],
        summary="Validate license",
        description="Check if a license key is valid and what products it provides access to.",
        request=ValidateLicenseSerializer,
        responses={200: ValidationResponseSerializer},
    )
    def post(self, request):
        serializer = ValidateLicenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Find the license key
        try:
            license_key = (
                LicenseKey.objects.select_related("brand")
                .prefetch_related("licenses__product", "licenses__activations")
                .get(key=data["license_key"], is_active=True)
            )
        except LicenseKey.DoesNotExist:
            raise LicenseKeyNotFoundError()

        # Filter by product if specified
        licenses = license_key.licenses.all()
        if "product_slug" in data:
            licenses = licenses.filter(product__slug=data["product_slug"])

        # Check instance activation if specified
        instance_id = data.get("instance_id")

        # Build license info
        license_data = []
        any_valid = False
        for license in licenses:
            is_valid = license.is_valid

            # If instance_id provided, also check if it's activated
            if instance_id and is_valid:
                is_activated = license.activations.filter(
                    instance_id=instance_id, is_active=True
                ).exists()
                if not is_activated:
                    is_valid = False

            if license.is_valid:
                any_valid = True

            license_data.append(
                {
                    "id": license.id,
                    "product": {
                        "id": license.product.id,
                        "name": license.product.name,
                        "slug": license.product.slug,
                    },
                    "status": license.status,
                    "expires_at": license.expires_at,
                    "is_valid": is_valid,
                    "seat_limit": license.seat_limit,
                    "seats_used": license.seats_used,
                    "seats_available": license.seats_available,
                }
            )

        # Update last check for any matching activations
        if instance_id:
            Activation.objects.filter(
                license__license_key=license_key,
                instance_id=instance_id,
                is_active=True,
            ).update(last_check_at=timezone.now())

        response_data = {
            "is_valid": any_valid,
            "license_key": license_key.key,
            "licenses": license_data,
        }

        logger.info(f"License validated: {license_key.key[:8]}... - valid: {any_valid}")

        return Response({"data": response_data})


class DeactivateLicenseView(APIView):
    """
    Deactivate a license for a specific instance.
    US5: End-user product or customer can deactivate a seat.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Product API"],
        summary="Deactivate license",
        description="Deactivate a license for a specific instance, freeing a seat.",
        request=DeactivateLicenseSerializer,
        responses={200: dict},
    )
    def post(self, request):
        serializer = DeactivateLicenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Find the license key
        try:
            license_key = LicenseKey.objects.get(
                key=data["license_key"], is_active=True
            )
        except LicenseKey.DoesNotExist:
            raise LicenseKeyNotFoundError()

        # Find the license
        try:
            license = License.objects.get(
                license_key=license_key, product__slug=data["product_slug"]
            )
        except License.DoesNotExist:
            raise LicenseNotFoundError()

        # Find and deactivate the activation
        try:
            activation = Activation.objects.get(
                license=license, instance_id=data["instance_id"], is_active=True
            )
        except Activation.DoesNotExist:
            raise ActivationNotFoundError(
                detail=f"No active activation found for instance '{data['instance_id']}'"
            )

        activation.deactivate()
        logger.info(f"License deactivated: {license.id} on {data['instance_id']}")

        return Response(
            {
                "data": {
                    "message": "License deactivated successfully",
                    "instance_id": data["instance_id"],
                    "seats_used": license.seats_used,
                    "seats_available": license.seats_available,
                }
            }
        )


class LicenseStatusView(APIView):
    """
    Get full status of a license key.
    US4: User can check license status.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Product API"],
        summary="Get license status",
        description="Get detailed status of a license key including all licenses and activations.",
        responses={200: LicenseStatusResponseSerializer},
    )
    def get(self, request):
        license_key_value = request.query_params.get("license_key")
        if not license_key_value:
            return Response(
                {
                    "error": {
                        "code": "missing_parameter",
                        "message": "license_key is required",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            license_key = (
                LicenseKey.objects.select_related("brand")
                .prefetch_related("licenses__product", "licenses__activations")
                .get(key=license_key_value, is_active=True)
            )
        except LicenseKey.DoesNotExist:
            raise LicenseKeyNotFoundError()

        # Build response
        licenses_data = []
        activations_data = []

        for license in license_key.licenses.all():
            licenses_data.append(
                {
                    "id": license.id,
                    "product": {
                        "id": license.product.id,
                        "name": license.product.name,
                        "slug": license.product.slug,
                    },
                    "status": license.status,
                    "expires_at": license.expires_at,
                    "is_valid": license.is_valid,
                    "seat_limit": license.seat_limit,
                    "seats_used": license.seats_used,
                    "seats_available": license.seats_available,
                }
            )

            for activation in license.activations.filter(is_active=True):
                activations_data.append(
                    {
                        "id": activation.id,
                        "instance_id": activation.instance_id,
                        "instance_name": activation.instance_name,
                        "is_active": activation.is_active,
                        "activated_at": activation.activated_at,
                    }
                )

        response_data = {
            "license_key": license_key.key,
            "customer_email": license_key.customer_email,
            "brand": license_key.brand.name,
            "licenses": licenses_data,
            "activations": activations_data,
        }

        return Response({"data": response_data})
