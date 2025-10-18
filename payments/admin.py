from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("label","service_name","customer_fio","amount","status","operation_id","created")
    search_fields = ("label","operation_id","payer","service_name","customer_fio")
    list_filter = ("status",)
