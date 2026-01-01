from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """
    Admin interface for managing applications
    """

    list_display = [
        "id",
        "full_name",
        "applicant_type",
        "email",
        "phone",
        "status_badge",
        "created_at",
        "telegram_link",
    ]
    list_filter = ["status", "applicant_type", "created_at"]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "parent_first_name",
        "parent_last_name",
    ]
    readonly_fields = [
        "id",
        "tracking_token",
        "created_at",
        "processed_at",
        "processed_by",
        "generated_username",
        "parent_username",
        "telegram_message_id",
    ]

    fieldsets = (
        (
            "Personal Information",
            {"fields": ("first_name", "last_name", "email", "phone", "telegram_id")},
        ),
        (
            "Application Details",
            {
                "fields": (
                    "applicant_type",
                    "grade",
                    "subject",
                    "experience",
                    "motivation",
                )
            },
        ),
        (
            "Parent Information",
            {
                "fields": (
                    "parent_first_name",
                    "parent_last_name",
                    "parent_email",
                    "parent_phone",
                    "parent_telegram_id",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Status and Processing",
            {"fields": ("status", "notes", "processed_at", "processed_by")},
        ),
        (
            "System Information",
            {
                "fields": ("id", "tracking_token", "created_at", "telegram_message_id"),
                "classes": ("collapse",),
            },
        ),
        (
            "Generated Credentials",
            {
                "fields": ("generated_username", "parent_username"),
                "classes": ("collapse",),
            },
        ),
    )

    def status_badge(self, obj):
        """
        Display status with colored badge
        """
        colors = {
            Application.Status.PENDING: "orange",
            Application.Status.APPROVED: "green",
            Application.Status.REJECTED: "red",
        }

        emojis = {
            Application.Status.PENDING: "⏳",
            Application.Status.APPROVED: "✅",
            Application.Status.REJECTED: "❌",
        }

        color = colors.get(obj.status, "gray")
        emoji = emojis.get(obj.status, "📝")

        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}",
        )

    status_badge.short_description = "Status"

    def telegram_link(self, obj):
        """
        Link to Telegram message
        """
        if obj.telegram_message_id:
            return format_html(
                '<a href="https://t.me/c/{}/{}" target="_blank" style="color: #0088cc;">📱 Telegram</a>',
                obj.telegram_message_id.split("_")[0]
                if "_" in obj.telegram_message_id
                else obj.telegram_message_id,
                obj.telegram_message_id.split("_")[1]
                if "_" in obj.telegram_message_id
                else obj.telegram_message_id,
            )
        return "—"

    telegram_link.short_description = "Telegram"

    def get_queryset(self, request):
        """
        Optimized query
        """
        return super().get_queryset(request).select_related("processed_by")

    def save_model(self, request, obj, form, change):
        """
        Automatically update processed_at when status changes
        """
        if change and "status" in form.changed_data:
            from django.utils import timezone

            if obj.status != Application.Status.PENDING and not obj.processed_at:
                obj.processed_at = timezone.now()
                obj.processed_by = request.user

        super().save_model(request, obj, form, change)

    actions = ["mark_as_approved", "mark_as_rejected"]

    def mark_as_approved(self, request, queryset):
        """
        Mark applications as approved
        """
        from django.utils import timezone

        updated = queryset.filter(status=Application.Status.PENDING).update(
            status=Application.Status.APPROVED,
            processed_at=timezone.now(),
            processed_by=request.user,
        )
        self.message_user(request, f"{updated} applications marked as approved")

    mark_as_approved.short_description = "Mark as approved"

    def mark_as_rejected(self, request, queryset):
        """
        Mark applications as rejected
        """
        from django.utils import timezone

        updated = queryset.filter(status=Application.Status.PENDING).update(
            status=Application.Status.REJECTED,
            processed_at=timezone.now(),
            processed_by=request.user,
        )
        self.message_user(request, f"{updated} applications marked as rejected")

    mark_as_rejected.short_description = "Mark as rejected"
