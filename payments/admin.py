from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("yookassa_payment_id","service_name","customer_fio","amount","status","created","paid_at")
    search_fields = ("yookassa_payment_id","service_name","customer_fio","description")
    list_filter = ("status","created")
    readonly_fields = ("yookassa_payment_id","confirmation_url","raw_response","created","updated","paid_at")
    fieldsets = (
        ("Основная информация", {
            "fields": ("yookassa_payment_id","amount","status","service_name","customer_fio","description")
        }),
        ("URL и метаданные", {
            "fields": ("confirmation_url","return_url","metadata","raw_response")
        }),
        ("Временные метки", {
            "fields": ("created","updated","paid_at")
        }),
    )
