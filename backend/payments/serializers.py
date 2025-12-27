from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id',
            'yookassa_payment_id',
            'amount',
            'status',
            'service_name',
            'customer_fio',
            'description',
            'confirmation_url',
            'return_url',
            'metadata',
            'created',
            'updated',
            'paid_at'
        ]
        read_only_fields = [
            'id',
            'yookassa_payment_id',
            'status',
            'confirmation_url',
            'created',
            'updated',
            'paid_at'
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'amount',
            'service_name',
            'customer_fio',
            'description',
            'return_url',
            'metadata'
        ]

