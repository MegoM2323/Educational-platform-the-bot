"""
Комплексные unit-тесты для payments/views.py

Покрывает:
- YooKassa Webhook Handler (payment.succeeded, payment.canceled, refund.succeeded)
- Payment creation через create_yookassa_payment()
- Payment status checking (check_payment_status)
- PaymentViewSet API endpoints
"""
import pytest
import json
from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock
from django.utils import timezone
from django.test import RequestFactory
from django.core.cache import cache

from payments.models import Payment
from payments.views import (
    yookassa_webhook,
    check_payment_status,
    create_yookassa_payment,
    check_yookassa_payment_status,
    verify_yookassa_ip,
    PaymentViewSet
)
from materials.models import SubjectPayment, SubjectEnrollment, SubjectSubscription


# ===== YooKassa Webhook Handler Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestYooKassaWebhook:
    """Тесты для webhook обработчика от YooKassa"""

    def test_webhook_payment_succeeded(self, client, payment, subject_payment):
        """Успешная обработка webhook payment.succeeded"""
        # Связываем payment с yookassa_payment_id
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.save()

        webhook_data = {
            'type': 'payment.succeeded',
            'event': 'payment.succeeded',
            'object': {
                'id': 'test-payment-webhook-123',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                },
                'created_at': timezone.now().isoformat(),
                'captured_at': timezone.now().isoformat(),
            }
        }

        # Mock IP verification
        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200
        assert response.content == b'OK'

        # Проверяем, что Payment обновлен
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert payment.paid_at is not None

        # Проверяем, что SubjectPayment обновлен
        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.PAID
        assert subject_payment.paid_at is not None

    def test_webhook_payment_succeeded_idempotency(self, client, payment, subject_payment):
        """Webhook payment.succeeded обрабатывается идемпотентно (не дублирует операции)"""
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.status = Payment.Status.SUCCEEDED  # Уже обработан
        payment.paid_at = timezone.now()
        payment.save()

        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.paid_at = timezone.now()
        subject_payment.save()

        webhook_data = {
            'type': 'payment.succeeded',
            'event': 'payment.succeeded',
            'object': {
                'id': 'test-payment-webhook-123',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                }
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200

        # Проверяем, что статусы не изменились
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED

    def test_webhook_payment_canceled(self, client, payment, subject_payment):
        """Успешная обработка webhook payment.canceled"""
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.save()

        subject_payment.status = SubjectPayment.Status.WAITING_FOR_PAYMENT
        subject_payment.save()

        webhook_data = {
            'type': 'payment.canceled',
            'event': 'payment.canceled',
            'object': {
                'id': 'test-payment-webhook-123',
                'status': 'canceled',
                'paid': False,
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                },
                'canceled_at': timezone.now().isoformat()
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200

        # Проверяем статусы
        payment.refresh_from_db()
        assert payment.status == Payment.Status.CANCELED

        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.PENDING

    def test_webhook_payment_waiting_for_capture(self, client, payment, subject_payment):
        """Обработка webhook payment.waiting_for_capture"""
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.save()

        webhook_data = {
            'type': 'payment.waiting_for_capture',
            'event': 'payment.waiting_for_capture',
            'object': {
                'id': 'test-payment-webhook-123',
                'status': 'waiting_for_capture',
                'paid': True,
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                }
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200

        payment.refresh_from_db()
        assert payment.status == Payment.Status.WAITING_FOR_CAPTURE

        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.WAITING_FOR_PAYMENT

    def test_webhook_payment_failed(self, client, payment, subject_payment):
        """Обработка webhook payment.failed"""
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.save()

        subject_payment.status = SubjectPayment.Status.WAITING_FOR_PAYMENT
        subject_payment.save()

        webhook_data = {
            'type': 'payment.failed',
            'event': 'payment.failed',
            'object': {
                'id': 'test-payment-webhook-123',
                'status': 'failed',
                'paid': False,
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                }
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200

        payment.refresh_from_db()
        assert payment.status == Payment.Status.FAILED

        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.PENDING

    def test_webhook_refund_succeeded(self, client, payment, subject_payment):
        """Обработка webhook refund.succeeded"""
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.status = Payment.Status.SUCCEEDED
        payment.save()

        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.save()

        webhook_data = {
            'type': 'refund.succeeded',
            'event': 'refund.succeeded',
            'object': {
                'id': 'test-refund-123',
                'status': 'succeeded',
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                },
                'payment_id': 'test-payment-webhook-123'
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200

        payment.refresh_from_db()
        assert payment.status == Payment.Status.REFUNDED

        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.REFUNDED

    def test_webhook_unauthorized_ip(self, client, payment):
        """Webhook от неавторизованного IP должен быть отклонен"""
        webhook_data = {
            'type': 'payment.succeeded',
            'object': {
                'id': 'test-payment-123',
                'status': 'succeeded'
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=False):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 403

    def test_webhook_invalid_json(self, client):
        """Webhook с невалидным JSON должен вернуть 400"""
        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data='invalid json',
                content_type='application/json'
            )

        assert response.status_code == 400

    def test_webhook_missing_payment_id(self, client):
        """Webhook без payment ID должен вернуть 400"""
        webhook_data = {
            'type': 'payment.succeeded',
            'object': {
                'status': 'succeeded'
                # 'id' отсутствует
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 400

    def test_webhook_payment_not_found(self, client):
        """Webhook для несуществующего payment должен вернуть 400"""
        webhook_data = {
            'type': 'payment.succeeded',
            'object': {
                'id': 'non-existent-payment-id',
                'status': 'succeeded'
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 400

    def test_webhook_non_post_method(self, client):
        """Webhook должен принимать только POST запросы"""
        response = client.get('/yookassa-webhook/')
        assert response.status_code == 400

    def test_webhook_unsupported_event_type(self, client, payment):
        """Webhook с неподдерживаемым типом события игнорируется"""
        payment.yookassa_payment_id = 'test-payment-123'
        payment.save()

        webhook_data = {
            'type': 'payment.unsupported_event',
            'object': {
                'id': 'test-payment-123',
                'status': 'pending'
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200  # OK, но не обрабатывается

    def test_webhook_invalidates_cache_on_success(self, client, payment, subject_payment):
        """Webhook должен инвалидировать кеш статуса платежа"""
        payment.yookassa_payment_id = 'test-payment-webhook-123'
        payment.save()

        # Сначала кешируем статус
        cache_key = f"yookassa_status_{payment.yookassa_payment_id}"
        cache.set(cache_key, 'pending', 5)

        webhook_data = {
            'type': 'payment.succeeded',
            'object': {
                'id': 'test-payment-webhook-123',
                'status': 'succeeded',
                'paid': True,
                'amount': {
                    'value': '100.00',
                    'currency': 'RUB'
                }
            }
        }

        with patch('payments.views.verify_yookassa_ip', return_value=True):
            response = client.post(
                '/yookassa-webhook/',
                data=json.dumps(webhook_data),
                content_type='application/json'
            )

        assert response.status_code == 200

        # Проверяем, что кеш инвалидирован
        cached_status = cache.get(cache_key)
        assert cached_status is None


# ===== Payment Creation Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestCreateYooKassaPayment:
    """Тесты для создания платежа в YooKassa"""

    def test_create_payment_success(self, payment):
        """Успешное создание платежа в YooKassa"""
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_HOST'] = 'localhost:8000'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'yookassa-payment-id-123',
            'status': 'pending',
            'amount': {
                'value': '100.00',
                'currency': 'RUB'
            },
            'confirmation': {
                'type': 'redirect',
                'confirmation_url': 'https://yookassa.ru/checkout/test-123'
            },
            'metadata': payment.metadata
        }

        with patch('requests.post', return_value=mock_response):
            result = create_yookassa_payment(payment, request)

        assert result is not None
        assert 'id' in result
        assert result['id'] == 'yookassa-payment-id-123'
        assert 'confirmation' in result

    def test_create_payment_missing_credentials(self, payment, settings):
        """Ошибка при отсутствующих credentials"""
        settings.YOOKASSA_SHOP_ID = None
        settings.YOOKASSA_SECRET_KEY = None

        factory = RequestFactory()
        request = factory.get('/')

        result = create_yookassa_payment(payment, request)

        assert 'error' in result
        assert result['error_type'] == 'configuration_error'

    def test_create_payment_invalid_amount(self):
        """Ошибка при некорректной сумме платежа"""
        payment = Payment.objects.create(
            amount=Decimal('0.00'),  # Невалидная сумма
            service_name="Test",
            customer_fio="Test User"
        )

        factory = RequestFactory()
        request = factory.get('/')

        result = create_yookassa_payment(payment, request)

        assert 'error' in result
        assert result['error_type'] == 'invalid_amount'

    def test_create_payment_yookassa_api_error(self, payment):
        """Обработка ошибки от YooKassa API"""
        factory = RequestFactory()
        request = factory.get('/')

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_response.json.return_value = {
            'code': 'invalid_credentials',
            'description': 'Invalid shop credentials'
        }

        with patch('requests.post', return_value=mock_response):
            result = create_yookassa_payment(payment, request)

        assert 'error' in result
        assert result['error_type'] == 'yookassa_api_error'
        assert result['status_code'] == 401

    def test_create_payment_network_timeout(self, payment):
        """Обработка таймаута при обращении к API"""
        factory = RequestFactory()
        request = factory.get('/')

        with patch('requests.post', side_effect=Exception('Timeout')):
            result = create_yookassa_payment(payment, request)

        assert 'error' in result
        assert result['error_type'] == 'unexpected_error'

    def test_create_payment_metadata_preserved(self, payment):
        """Метаданные сохраняются при создании платежа"""
        payment.metadata = {
            'subject_payment_id': 123,
            'enrollment_id': 456,
            'custom_data': 'test'
        }
        payment.save()

        factory = RequestFactory()
        request = factory.get('/')

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'id': 'yookassa-payment-id',
            'status': 'pending',
            'amount': {'value': '100.00', 'currency': 'RUB'},
            'confirmation': {
                'type': 'redirect',
                'confirmation_url': 'https://yookassa.ru/checkout/test'
            },
            'metadata': payment.metadata
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            result = create_yookassa_payment(payment, request)

        # Проверяем, что метаданные были отправлены
        call_args = mock_post.call_args
        sent_data = json.loads(call_args[1]['data'])
        assert sent_data['metadata'] == payment.metadata


# ===== Payment Status Checking Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestCheckPaymentStatus:
    """Тесты для проверки статуса платежа"""

    def test_check_status_succeeded_payment(self, client, payment):
        """Проверка статуса для успешного платежа"""
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save()

        response = client.get(f'/check-payment-status/?payment_id={payment.id}')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == Payment.Status.SUCCEEDED
        assert 'paid_at' in data

    def test_check_status_pending_payment_with_yookassa_check(self, client, payment):
        """Проверка статуса pending платежа с запросом к YooKassa"""
        payment.yookassa_payment_id = 'test-yookassa-id'
        payment.status = Payment.Status.PENDING
        payment.save()

        with patch('payments.views.check_yookassa_payment_status', return_value='pending'):
            response = client.get(f'/check-payment-status/?payment_id={payment.id}')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == Payment.Status.PENDING

    def test_check_status_payment_not_found(self, client):
        """Ошибка при запросе несуществующего платежа"""
        response = client.get('/check-payment-status/?payment_id=00000000-0000-0000-0000-000000000000')

        assert response.status_code == 404

    def test_check_status_missing_payment_id(self, client):
        """Ошибка при отсутствии payment_id"""
        response = client.get('/check-payment-status/')

        assert response.status_code == 400

    def test_check_status_non_get_method(self, client, payment):
        """Endpoint принимает только GET запросы"""
        response = client.post(f'/check-payment-status/?payment_id={payment.id}')

        assert response.status_code == 405

    def test_check_status_uses_cache(self, client, payment):
        """Проверка статуса использует кеш для YooKassa запросов"""
        payment.yookassa_payment_id = 'test-yookassa-id'
        payment.status = Payment.Status.PENDING
        payment.save()

        cache_key = f"yookassa_status_{payment.yookassa_payment_id}"
        cache.set(cache_key, 'pending', 5)

        with patch('payments.views.check_yookassa_payment_status') as mock_check:
            response = client.get(f'/check-payment-status/?payment_id={payment.id}')

        # Не должен вызывать YooKassa API, т.к. есть в кеше
        mock_check.assert_not_called()

        assert response.status_code == 200


# ===== YooKassa IP Verification Tests =====

@pytest.mark.unit
class TestVerifyYooKassaIP:
    """Тесты для проверки IP адресов YooKassa"""

    def test_verify_valid_ip(self):
        """Проверка валидного IP из разрешенного диапазона"""
        factory = RequestFactory()
        request = factory.post('/')
        request.META['REMOTE_ADDR'] = '185.71.76.1'

        assert verify_yookassa_ip(request) is True

    def test_verify_invalid_ip(self):
        """Проверка невалидного IP"""
        factory = RequestFactory()
        request = factory.post('/')
        request.META['REMOTE_ADDR'] = '1.2.3.4'

        assert verify_yookassa_ip(request) is False

    def test_verify_x_forwarded_for(self):
        """Проверка IP из X-Forwarded-For заголовка"""
        factory = RequestFactory()
        request = factory.post('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '185.71.76.5, 10.0.0.1'

        assert verify_yookassa_ip(request) is True

    def test_verify_missing_ip(self):
        """Проверка при отсутствии IP"""
        factory = RequestFactory()
        request = factory.post('/')
        # Не устанавливаем REMOTE_ADDR

        assert verify_yookassa_ip(request) is False


# ===== PaymentViewSet API Tests =====

@pytest.mark.unit
@pytest.mark.django_db
class TestPaymentViewSet:
    """Тесты для PaymentViewSet API endpoints"""

    def test_create_payment_api_success(self, client, enrollment):
        """Успешное создание платежа через API"""
        payment_data = {
            'amount': '100.00',
            'service_name': 'Test Subject',
            'customer_fio': 'Test User',
            'description': 'Test payment',
            'metadata': {
                'enrollment_id': enrollment.id,
                'subject_payment_id': None
            }
        }

        mock_response = {
            'id': 'yookassa-payment-id-123',
            'status': 'pending',
            'amount': {'value': '100.00', 'currency': 'RUB'},
            'confirmation': {
                'type': 'redirect',
                'confirmation_url': 'https://yookassa.ru/checkout/test'
            }
        }

        with patch('payments.views.create_yookassa_payment', return_value=mock_response):
            response = client.post(
                '/api/payments/',
                data=json.dumps(payment_data),
                content_type='application/json'
            )

        assert response.status_code == 201
        data = response.json()
        assert 'yookassa_payment_id' in data
        assert data['confirmation_url'] is not None

    def test_create_payment_api_yookassa_error(self, client):
        """Обработка ошибки YooKassa при создании платежа"""
        payment_data = {
            'amount': '100.00',
            'service_name': 'Test',
            'customer_fio': 'Test User'
        }

        error_response = {
            'error': 'YooKassa API error',
            'error_type': 'yookassa_api_error',
            'technical_details': 'Invalid credentials'
        }

        with patch('payments.views.create_yookassa_payment', return_value=error_response):
            response = client.post(
                '/api/payments/',
                data=json.dumps(payment_data),
                content_type='application/json'
            )

        assert response.status_code == 400
        data = response.json()
        assert 'error' in data

    def test_payment_status_api_succeeded(self, client, payment):
        """API endpoint для проверки статуса успешного платежа"""
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save()

        response = client.get(f'/api/payments/{payment.id}/status/')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == Payment.Status.SUCCEEDED

    def test_payment_status_api_pending_with_polling(self, client, payment):
        """API endpoint проверяет YooKassa для pending платежей"""
        payment.yookassa_payment_id = 'test-yookassa-id'
        payment.status = Payment.Status.PENDING
        payment.save()

        with patch('payments.views.check_yookassa_payment_status', return_value='pending'):
            response = client.get(f'/api/payments/{payment.id}/status/')

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == Payment.Status.PENDING
