"""
License, LicenseKey, and Activation models for license management.
"""
import secrets
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.brands.models import Brand, Product


class LicenseStatus(models.TextChoices):
    """License status choices."""

    VALID = "valid", "Valid"
    SUSPENDED = "suspended", "Suspended"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class LicenseKey(models.Model):
    """
    Customer-facing license key that can unlock multiple licenses.
    A customer may have one license key per brand, with multiple product licenses attached.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The actual key shown to customers
    key = models.CharField(max_length=64, unique=True, editable=False)

    # Customer identification
    customer_email = models.EmailField(db_index=True)
    customer_name = models.CharField(max_length=255, blank=True)

    # Brand association (a license key belongs to one brand)
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="license_keys"
    )

    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "license_keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer_email"]),
            models.Index(fields=["brand", "customer_email"]),
        ]

    def __str__(self) -> str:
        return f"{self.key[:8]}... ({self.customer_email})"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self._generate_key()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_key() -> str:
        """Generate a unique, URL-safe license key."""
        return secrets.token_urlsafe(32)


class License(models.Model):
    """
    Individual license for a specific product.
    Multiple licenses can be attached to a single license key.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    license_key = models.ForeignKey(
        LicenseKey, on_delete=models.CASCADE, related_name="licenses"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="licenses"
    )

    # License details
    status = models.CharField(
        max_length=20, choices=LicenseStatus.choices, default=LicenseStatus.VALID
    )
    expires_at = models.DateTimeField()

    # Seat management (0 = unlimited)
    seat_limit = models.PositiveIntegerField(default=1)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "licenses"
        ordering = ["-created_at"]
        unique_together = [["license_key", "product"]]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"License {self.id} - {self.product.name} ({self.status})"

    @property
    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self.status != LicenseStatus.VALID:
            return False
        if self.expires_at < timezone.now():
            return False
        return True

    @property
    def seats_used(self) -> int:
        """Count of active activations."""
        return self.activations.filter(is_active=True).count()

    @property
    def seats_available(self) -> int:
        """Number of seats still available (None if unlimited)."""
        if self.seat_limit == 0:
            return None
        return max(0, self.seat_limit - self.seats_used)

    def can_activate(self) -> bool:
        """Check if a new activation is allowed."""
        if not self.is_valid:
            return False
        if self.seat_limit == 0:  # Unlimited
            return True
        return self.seats_used < self.seat_limit

    def renew(self, days: int = 365) -> None:
        """Extend the license expiration."""
        if self.expires_at < timezone.now():
            self.expires_at = timezone.now() + timedelta(days=days)
        else:
            self.expires_at = self.expires_at + timedelta(days=days)
        self.status = LicenseStatus.VALID
        self.save(update_fields=["expires_at", "status", "updated_at"])

    def suspend(self) -> None:
        """Suspend the license."""
        self.status = LicenseStatus.SUSPENDED
        self.save(update_fields=["status", "updated_at"])

    def resume(self) -> None:
        """Resume a suspended license."""
        if self.status == LicenseStatus.SUSPENDED:
            self.status = LicenseStatus.VALID
            self.save(update_fields=["status", "updated_at"])

    def cancel(self) -> None:
        """Cancel the license."""
        self.status = LicenseStatus.CANCELLED
        self.save(update_fields=["status", "updated_at"])


class Activation(models.Model):
    """
    Represents an activation of a license on a specific instance.
    Each activation consumes one seat.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    license = models.ForeignKey(
        License, on_delete=models.CASCADE, related_name="activations"
    )

    # Instance identification (site URL, machine ID, etc.)
    instance_id = models.CharField(max_length=255)
    instance_name = models.CharField(max_length=255, blank=True)

    # Additional instance metadata
    instance_metadata = models.JSONField(default=dict, blank=True)

    # Activation status
    is_active = models.BooleanField(default=True)
    activated_at = models.DateTimeField(auto_now_add=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    last_check_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "activations"
        ordering = ["-activated_at"]
        unique_together = [["license", "instance_id"]]
        indexes = [
            models.Index(fields=["instance_id"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"Activation {self.instance_id} ({status})"

    def deactivate(self) -> None:
        """Deactivate this activation, freeing the seat."""
        self.is_active = False
        self.deactivated_at = timezone.now()
        self.save(update_fields=["is_active", "deactivated_at"])

    def record_check(self) -> None:
        """Record a license check from this instance."""
        self.last_check_at = timezone.now()
        self.save(update_fields=["last_check_at"])
