import factory
import uuid
from factory.django import DjangoModelFactory
from decimal import Decimal
from django.utils import timezone
from .models import Payment


class PaymentFactory(DjangoModelFactory):
    class Meta:
        model = Payment

    id = factory.LazyFunction(uuid.uuid4)
    yookassa_payment_id = factory.Sequence(lambda n: f"yookassa_{n}")
    amount = Decimal("100.00")
    status = Payment.Status.PENDING
    service_name = "Test Service"
    customer_fio = "Test User"
    description = "Test payment"
    confirmation_url = "https://example.com/confirm"
    return_url = "https://example.com/return"
    metadata = {"order_id": 123}
    raw_response = {}
