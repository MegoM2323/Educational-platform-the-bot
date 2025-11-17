import uuid
from django.db import models

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        WAITING_FOR_CAPTURE = "waiting_for_capture", "Waiting for Capture"
        SUCCEEDED = "succeeded", "Succeeded"
        CANCELED = "canceled", "Canceled"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    # Основные поля
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    yookassa_payment_id = models.CharField(max_length=255, unique=True, blank=True, null=True, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Информация о платеже
    service_name = models.CharField(max_length=255, blank=True, default="")
    customer_fio = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    
    # URL для подтверждения и возврата
    confirmation_url = models.URLField(blank=True, null=True)
    return_url = models.URLField(blank=True, null=True)
    
    # Метаданные и сырые данные
    metadata = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    
    # Временные метки
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"Payment {self.yookassa_payment_id or self.id} - {self.amount} {self.status}"