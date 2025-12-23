from django.contrib import admin

from .models import Activation, License, LicenseKey


class LicenseInline(admin.TabularInline):
    model = License
    extra = 0
    readonly_fields = ['id', 'created_at']
    fields = ['product', 'status', 'expires_at', 'seat_limit', 'created_at']


class ActivationInline(admin.TabularInline):
    model = Activation
    extra = 0
    readonly_fields = ['id', 'activated_at', 'deactivated_at', 'last_check_at']
    fields = ['instance_id', 'instance_name', 'is_active', 'activated_at', 'last_check_at']


@admin.register(LicenseKey)
class LicenseKeyAdmin(admin.ModelAdmin):
    list_display = ['key_preview', 'customer_email', 'brand', 'is_active', 'created_at']
    list_filter = ['brand', 'is_active']
    search_fields = ['key', 'customer_email', 'customer_name']
    readonly_fields = ['id', 'key', 'created_at', 'updated_at']
    inlines = [LicenseInline]

    def key_preview(self, obj):
        return f"{obj.key[:12]}..."
    key_preview.short_description = 'License Key'


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ['id', 'product', 'license_key', 'status', 'expires_at', 'seats_used', 'seat_limit']
    list_filter = ['status', 'product__brand', 'product']
    search_fields = ['license_key__key', 'license_key__customer_email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'seats_used']
    inlines = [ActivationInline]

    def seats_used(self, obj):
        return obj.seats_used
    seats_used.short_description = 'Seats Used'


@admin.register(Activation)
class ActivationAdmin(admin.ModelAdmin):
    list_display = ['instance_id', 'license', 'is_active', 'activated_at', 'last_check_at']
    list_filter = ['is_active', 'license__product__brand']
    search_fields = ['instance_id', 'instance_name', 'license__license_key__key']
    readonly_fields = ['id', 'activated_at', 'deactivated_at', 'last_check_at']
