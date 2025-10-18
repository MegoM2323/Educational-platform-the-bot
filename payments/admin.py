from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("label","amount","status","operation_id","created")
    list_filter = ("status",)
    search_fields = ("label","operation_id","payer")
