"""
Admin configuration for notification channel models.

Provides admin interface for managing device tokens and phone numbers.
"""

from django.contrib import admin

from .models import DeviceToken, UserPhoneNumber


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """Admin interface for DeviceToken model."""

    list_display = (
        'user_email',
        'get_device_type_display',
        'device_name',
        'is_active',
        'last_used_at',
        'created_at',
    )

    list_filter = (
        'device_type',
        'is_active',
        'created_at',
        'last_used_at',
    )

    search_fields = (
        'user__email',
        'user__username',
        'device_name',
        'token',
    )

    readonly_fields = (
        'token',
        'created_at',
        'updated_at',
        'last_used_at',
    )

    fieldsets = (
        ('User Information', {
            'fields': ('user',),
        }),
        ('Device Details', {
            'fields': (
                'token',
                'device_type',
                'device_name',
                'is_active',
            ),
        }),
        ('Metadata', {
            'fields': (
                'last_used_at',
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def user_email(self, obj):
        """Display user email in list view."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def has_add_permission(self, request):
        """Prevent manual creation of device tokens in admin."""
        return False


@admin.register(UserPhoneNumber)
class UserPhoneNumberAdmin(admin.ModelAdmin):
    """Admin interface for UserPhoneNumber model."""

    list_display = (
        'user_email',
        'phone_number',
        'get_status_display',
        'verification_attempts',
        'verified_at',
        'created_at',
    )

    list_filter = (
        'status',
        'created_at',
        'verified_at',
    )

    search_fields = (
        'user__email',
        'user__username',
        'phone_number',
    )

    readonly_fields = (
        'verification_code',
        'verification_attempts',
        'verified_at',
        'created_at',
        'updated_at',
    )

    fieldsets = (
        ('User Information', {
            'fields': ('user',),
        }),
        ('Phone Details', {
            'fields': (
                'phone_number',
                'status',
                'verification_code',
                'verification_attempts',
            ),
        }),
        ('Verification', {
            'fields': ('verified_at',),
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    def user_email(self, obj):
        """Display user email in list view."""
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email'

    def has_add_permission(self, request):
        """Prevent manual creation in admin."""
        return False
