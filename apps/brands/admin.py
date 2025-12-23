from django.contrib import admin

from .models import Brand, Product


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "api_key", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "brand", "default_seat_limit", "is_active", "created_at"]
    list_filter = ["brand", "is_active"]
    search_fields = ["name", "slug", "brand__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
