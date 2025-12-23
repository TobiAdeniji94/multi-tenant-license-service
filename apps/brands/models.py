"""
Brand and Product models for multi-tenant license management.
"""
import secrets
import uuid

from django.db import models


class Brand(models.Model):
    """
    Represents a tenant/brand in the system (e.g., WP Rocket, RankMath).
    Each brand has its own API credentials for authentication.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    
    # API Authentication
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    api_secret = models.CharField(max_length=128, editable=False)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brands'
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_hex(32)
        if not self.api_secret:
            self.api_secret = secrets.token_hex(64)
        super().save(*args, **kwargs)

    def regenerate_credentials(self) -> tuple[str, str]:
        """Regenerate API credentials. Returns (api_key, api_secret)."""
        self.api_key = secrets.token_hex(32)
        self.api_secret = secrets.token_hex(64)
        self.save(update_fields=['api_key', 'api_secret', 'updated_at'])
        return self.api_key, self.api_secret


class Product(models.Model):
    """
    Represents a product within a brand (e.g., RankMath Pro, Content AI).
    Licenses are issued for specific products.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name='products'
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    
    # Default seat limit for new licenses (0 = unlimited)
    default_seat_limit = models.PositiveIntegerField(default=1)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['brand', 'name']
        unique_together = [['brand', 'slug']]

    def __str__(self) -> str:
        return f"{self.brand.name} - {self.name}"
