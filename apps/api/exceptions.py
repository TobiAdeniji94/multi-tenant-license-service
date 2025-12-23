"""
Custom exception handling for the API.
"""
import logging
import uuid

from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error responses.
    """
    # Generate a unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]

    # Get the standard DRF response
    response = exception_handler(exc, context)

    if response is not None:
        # Restructure the response
        error_data = {
            "error": {
                "code": get_error_code(exc),
                "message": get_error_message(exc, response),
                "details": response.data
                if isinstance(response.data, dict)
                else {"detail": response.data},
            },
            "meta": {
                "request_id": request_id,
            },
        }
        response.data = error_data

        # Log the error
        logger.warning(
            "API Error [%s]: %s - %s",
            request_id,
            error_data["error"]["code"],
            error_data["error"]["message"],
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "error_code": error_data["error"]["code"],
            },
        )
    elif isinstance(exc, DjangoValidationError):
        # Handle Django validation errors
        error_data = {
            "error": {
                "code": "validation_error",
                "message": "Validation failed",
                "details": {
                    "errors": exc.messages if hasattr(exc, "messages") else [str(exc)]
                },
            },
            "meta": {
                "request_id": request_id,
            },
        }
        response = Response(error_data, status=status.HTTP_400_BAD_REQUEST)
        logger.warning(f"Validation Error [{request_id}]: {exc}")
    else:
        # Handle unexpected exceptions
        logger.exception(f"Unhandled Exception [{request_id}]: {exc}")
        error_data = {
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred",
                "details": {},
            },
            "meta": {
                "request_id": request_id,
            },
        }
        response = Response(error_data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response


def get_error_code(exc) -> str:
    """Get a machine-readable error code from an exception."""
    if hasattr(exc, "default_code"):
        return exc.default_code
    return exc.__class__.__name__.lower()


def get_error_message(exc, response) -> str:
    """Get a human-readable error message."""
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, str):
            return exc.detail
        elif isinstance(exc.detail, dict) and "detail" in exc.detail:
            return exc.detail["detail"]
    return str(exc)


# Custom API Exceptions
class LicenseNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "License not found"
    default_code = "license_not_found"


class LicenseKeyNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "License key not found"
    default_code = "license_key_not_found"


class LicenseInvalidError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "License is not valid"
    default_code = "license_invalid"


class LicenseExpiredError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "License has expired"
    default_code = "license_expired"


class SeatLimitExceededError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Seat limit exceeded"
    default_code = "seat_limit_exceeded"


class ActivationNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Activation not found"
    default_code = "activation_not_found"


class BrandAuthenticationError(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid brand credentials"
    default_code = "brand_auth_failed"


class ProductNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Product not found"
    default_code = "product_not_found"
