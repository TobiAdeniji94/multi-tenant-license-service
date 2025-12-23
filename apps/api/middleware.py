"""
API middleware for logging, request tracking, and rate limiting.
"""
import logging
import time
import uuid

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    Middleware to log all API requests with timing and request ID.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.request_id = request_id

        # Record start time
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"Request [{request_id}]: {request.method} {request.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "remote_addr": self._get_client_ip(request),
            },
        )

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.info(
            f"Response [{request_id}]: {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        # Add request ID to response headers
        response["X-Request-ID"] = request_id

        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP from request headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
