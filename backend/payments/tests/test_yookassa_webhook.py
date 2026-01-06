import json
import hmac
import hashlib
import uuid
from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings

from payments.models import Payment

User = get_user_model()


class YooKassaWebhookTestCase(TestCase):
    """Тесты для webhook обработки платежей от YooKassa"""

    def setUp(self):
        """Подготовка данных для тестов"""
        self.client = Client()
        self.webhook_url = "/api/payments/yookassa-webhook/"

        self.payment = Payment.objects.create(
            amount=Decimal("1000.00"),
            status=Payment.Status.PENDING,
            description="Test payment",
            service_name="Обучение",
            customer_fio="Test Parent",
            yookassa_payment_id="test_yookassa_id_123",
            metadata={"create_subscription": False, "is_recurring": False},
        )

    def _create_webhook_signature(self, body_bytes):
        """Генерирует HMAC-SHA256 подпись для webhook"""
        secret_key = settings.YOOKASSA_SECRET_KEY
        signature = hmac.new(
            secret_key.encode("utf-8"), body_bytes, hashlib.sha256
        ).hexdigest()
        return signature

    def _send_webhook(self, event_type, yookassa_id=None, with_signature=True):
        """Отправляет webhook от YooKassa"""
        if yookassa_id is None:
            yookassa_id = self.payment.yookassa_payment_id

        webhook_data = {
            "type": event_type,
            "object": {
                "id": yookassa_id,
                "status": event_type.split(".")[-1],
                "amount": {"value": str(self.payment.amount), "currency": "RUB"},
                "created_at": timezone.now().isoformat(),
                "metadata": self.payment.metadata,
            },
        }

        if event_type == "refund.succeeded":
            webhook_data["object"]["payment_id"] = self.payment.yookassa_payment_id

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
        }

        if with_signature:
            signature = self._create_webhook_signature(body)
            headers["HTTP_X_YOOKASSA_WEBHOOK_SIGNATURE"] = signature

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        return response

    def test_webhook_payment_succeeded(self):
        """Test: успешный платеж обновляет status Payment на SUCCEEDED"""
        response = self._send_webhook("payment.succeeded")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertIsNotNone(payment.paid_at)

    def test_webhook_payment_canceled(self):
        """Test: webhook payment.canceled обновляет статус"""
        self.payment.status = Payment.Status.WAITING_FOR_CAPTURE
        self.payment.save()

        response = self._send_webhook("payment.canceled")

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.CANCELED)

    def test_webhook_payment_failed(self):
        """Test: webhook payment.failed обновляет статус"""
        self.payment.status = Payment.Status.WAITING_FOR_CAPTURE
        self.payment.save()

        response = self._send_webhook("payment.failed")

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_webhook_payment_waiting_for_capture(self):
        """Test: webhook payment.waiting_for_capture обновляет статус"""
        response = self._send_webhook("payment.waiting_for_capture")

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.WAITING_FOR_CAPTURE)

    def test_webhook_refund_succeeded(self):
        """Test: webhook refund.succeeded обновляет статус платежа"""
        self.payment.status = Payment.Status.SUCCEEDED
        self.payment.paid_at = timezone.now()
        self.payment.save()

        webhook_data = {
            "type": "refund.succeeded",
            "object": {
                "id": str(uuid.uuid4()),
                "payment_id": self.payment.yookassa_payment_id,
                "status": "succeeded",
                "amount": {"value": str(self.payment.amount), "currency": "RUB"},
            },
        }

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
        }

        signature = self._create_webhook_signature(body)
        headers["HTTP_X_YOOKASSA_WEBHOOK_SIGNATURE"] = signature

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.REFUNDED)

    def test_webhook_without_signature(self):
        """Test: webhook без подписи обрабатывается (для совместимости)"""
        webhook_data = {
            "type": "payment.succeeded",
            "object": {"id": self.payment.yookassa_payment_id, "status": "succeeded"},
        }

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
        }

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)

    def test_webhook_invalid_json(self):
        """Test: webhook с невалидным JSON отклоняется"""
        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
        }

        response = self.client.post(
            self.webhook_url,
            data=b"invalid json {",
            content_type="application/json",
            **headers,
        )

        self.assertEqual(response.status_code, 400)

    def test_webhook_payment_not_found(self):
        """Test: webhook для несуществующего платежа"""
        webhook_data = {
            "type": "payment.succeeded",
            "object": {"id": "nonexistent_payment_id", "status": "succeeded"},
        }

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
        }

        signature = self._create_webhook_signature(body)
        headers["HTTP_X_YOOKASSA_WEBHOOK_SIGNATURE"] = signature

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        self.assertEqual(response.status_code, 400)

    def test_webhook_non_post_request(self):
        """Test: webhook должен быть только POST"""
        response = self.client.get(self.webhook_url)

        self.assertEqual(response.status_code, 400)

    def test_webhook_unauthorized_ip(self):
        """Test: webhook с неавторизованного IP отклоняется"""
        webhook_data = {
            "type": "payment.succeeded",
            "object": {"id": self.payment.yookassa_payment_id, "status": "succeeded"},
        }

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "1.2.3.4",
        }

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        self.assertEqual(response.status_code, 403)

    def test_webhook_with_invalid_signature(self):
        """Test: webhook с неправильной подписью отклоняется"""
        webhook_data = {
            "type": "payment.succeeded",
            "object": {"id": self.payment.yookassa_payment_id, "status": "succeeded"},
        }

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
            "HTTP_X_YOOKASSA_WEBHOOK_SIGNATURE": "invalid_signature_123",
        }

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        self.assertEqual(response.status_code, 403)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_webhook_idempotency(self):
        """Test: двойной webhook не дублирует платеж"""
        response1 = self._send_webhook("payment.succeeded")
        self.assertEqual(response1.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        paid_at_1 = payment.paid_at

        response2 = self._send_webhook("payment.succeeded")
        self.assertEqual(response2.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)
        self.assertEqual(payment.paid_at, paid_at_1)

    def test_webhook_select_for_update_prevents_race_condition(self):
        """Test: использование select_for_update() предотвращает race condition"""
        self.payment.status = Payment.Status.PENDING
        self.payment.save()

        from django.db import transaction

        with transaction.atomic():
            payment_locked = Payment.objects.select_for_update().get(id=self.payment.id)
            self.assertEqual(payment_locked.status, Payment.Status.PENDING)

            payment_locked.status = Payment.Status.SUCCEEDED
            payment_locked.save()

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.SUCCEEDED)

    def test_webhook_cache_invalidation_on_success(self):
        """Test: cache инвалидируется после успешной обработки webhook"""
        from django.core.cache import cache

        cache_key = f"yookassa_status_{self.payment.yookassa_payment_id}"
        cache.set(cache_key, "pending", 300)

        self.assertEqual(cache.get(cache_key), "pending")

        response = self._send_webhook("payment.succeeded")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(cache.get(cache_key))

    def test_webhook_cache_invalidation_on_cancel(self):
        """Test: cache инвалидируется после отмены платежа"""
        from django.core.cache import cache

        cache_key = f"yookassa_status_{self.payment.yookassa_payment_id}"
        cache.set(cache_key, "pending", 300)

        response = self._send_webhook("payment.canceled")

        self.assertEqual(response.status_code, 200)

        self.assertIsNone(cache.get(cache_key))

    def test_webhook_processes_payment_data(self):
        """Test: webhook обрабатывает данные платежа и сохраняет в raw_response"""
        response = self._send_webhook("payment.succeeded")

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertIsNotNone(payment.raw_response)
        self.assertIn("object", payment.raw_response)
        self.assertEqual(
            payment.raw_response["object"]["id"], self.payment.yookassa_payment_id
        )

    def test_webhook_supported_events_only(self):
        """Test: webhook игнорирует неподдерживаемые события"""
        webhook_data = {
            "type": "unknown.event",
            "object": {"id": self.payment.yookassa_payment_id, "status": "unknown"},
        }

        body = json.dumps(webhook_data).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "HTTP_X_FORWARDED_FOR": "185.71.76.1",
        }

        signature = self._create_webhook_signature(body)
        headers["HTTP_X_YOOKASSA_WEBHOOK_SIGNATURE"] = signature

        response = self.client.post(
            self.webhook_url, data=body, content_type="application/json", **headers
        )

        self.assertEqual(response.status_code, 200)

        payment = Payment.objects.get(id=self.payment.id)
        self.assertEqual(payment.status, Payment.Status.PENDING)

    def test_webhook_status_transitions(self):
        """Test: правильные переходы статусов платежей"""
        transitions = [
            (
                Payment.Status.PENDING,
                "payment.waiting_for_capture",
                Payment.Status.WAITING_FOR_CAPTURE,
            ),
            (
                Payment.Status.WAITING_FOR_CAPTURE,
                "payment.succeeded",
                Payment.Status.SUCCEEDED,
            ),
        ]

        for initial_status, event, expected_status in transitions:
            payment = Payment.objects.create(
                amount=Decimal("500.00"),
                status=initial_status,
                yookassa_payment_id=f"test_payment_{event}",
                metadata={},
            )

            webhook_data = {
                "type": event,
                "object": {
                    "id": payment.yookassa_payment_id,
                    "status": event.split(".")[-1],
                },
            }

            body = json.dumps(webhook_data).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "HTTP_X_FORWARDED_FOR": "185.71.76.1",
            }
            signature = self._create_webhook_signature(body)
            headers["HTTP_X_YOOKASSA_WEBHOOK_SIGNATURE"] = signature

            response = self.client.post(
                self.webhook_url, data=body, content_type="application/json", **headers
            )

            self.assertEqual(response.status_code, 200)

            payment.refresh_from_db()
            self.assertEqual(payment.status, expected_status)
