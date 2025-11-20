"""
Тесты для рекуррентных платежей с использованием payment_method_id
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.management import call_command
from io import StringIO

from materials.models import SubjectSubscription, SubjectPayment
from payments.models import Payment


@pytest.mark.integration
@pytest.mark.recurring_payments
class TestRecurringPaymentsWithPaymentMethodId:
    """Тесты для автоматических рекуррентных платежей"""

    def test_creates_recurring_payment_with_payment_method_id(
        self,
        subscription,
        student_with_parent,
        mocker
    ):
        """Тест: создание рекуррентного платежа с сохраненным payment_method_id"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.payment_method_id = 'pm_test_123456789'
        subscription.save()

        # Mock YooKassa API
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')
        mock_yookassa.return_value = {
            'id': 'yookassa-payment-id-123',
            'status': 'pending',
            'confirmation': {
                'confirmation_url': 'https://test.url/payment'
            }
        }

        # Act
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'обработано 1' in output

        # Проверяем что платеж создан
        payments = Payment.objects.filter(
            metadata__subscription_id=subscription.id,
            metadata__is_recurring=True
        )
        assert payments.count() == 1

        payment = payments.first()
        assert payment.metadata['payment_method_id'] == 'pm_test_123456789'
        assert payment.metadata['is_recurring'] is True
        assert payment.metadata['create_subscription'] is False

    def test_skips_subscription_without_payment_method_id(
        self,
        subscription,
        student_with_parent,
        mocker
    ):
        """Тест: подписка БЕЗ payment_method_id пропускается"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.payment_method_id = None  # Нет сохраненного метода оплаты
        subscription.save()

        # Mock YooKassa API (не должен вызваться)
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')

        # Act
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'отсутствует payment_method_id' in output

        # Проверяем что платеж НЕ создан
        payments = Payment.objects.filter(
            metadata__subscription_id=subscription.id
        )
        assert payments.count() == 0

        # YooKassa API не вызывался
        mock_yookassa.assert_not_called()

    def test_payment_method_id_saved_on_first_payment(
        self,
        payment,
        subject_payment,
        subscription
    ):
        """Тест: payment_method_id сохраняется после первого успешного платежа"""
        # Arrange
        from payments.services import process_successful_payment

        # Имитируем webhook от YooKassa с сохраненным методом оплаты
        payment.status = Payment.Status.PENDING
        payment.metadata = {
            'create_subscription': True,
            'enrollment_id': subject_payment.enrollment.id
        }
        payment.raw_response = {
            'payment_method': {
                'id': 'pm_saved_from_webhook_123',
                'saved': True
            }
        }
        payment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True

        # Проверяем что payment_method_id сохранен в подписке
        subscription.refresh_from_db()
        assert subscription.payment_method_id == 'pm_saved_from_webhook_123'

    def test_recurring_payment_updates_subscription_next_date(
        self,
        subscription,
        student_with_parent,
        mocker,
        settings
    ):
        """Тест: next_payment_date обновляется сразу после создания платежа"""
        # Arrange
        settings.PAYMENT_DEVELOPMENT_MODE = True
        settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES = 15

        old_next_payment = timezone.now() - timedelta(minutes=1)
        subscription.next_payment_date = old_next_payment
        subscription.payment_method_id = 'pm_test_123'
        subscription.save()

        # Mock YooKassa API
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')
        mock_yookassa.return_value = {
            'id': 'test-payment-id',
            'status': 'pending',
            'confirmation': {
                'confirmation_url': 'https://test.url'
            }
        }

        # Act
        call_command('process_subscription_payments')

        # Assert
        subscription.refresh_from_db()

        # next_payment_date должна быть обновлена на будущее
        assert subscription.next_payment_date > timezone.now()
        assert subscription.next_payment_date > old_next_payment

        # Должна быть +15 минут в development mode
        expected_next = timezone.now() + timedelta(minutes=15)
        time_diff = abs((subscription.next_payment_date - expected_next).total_seconds())
        assert time_diff < 10  # Допуск 10 секунд

    def test_recurring_payment_creates_subject_payment(
        self,
        subscription,
        enrollment,
        student_with_parent,
        mocker
    ):
        """Тест: создается SubjectPayment при рекуррентном платеже"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.payment_method_id = 'pm_test_123'
        subscription.amount = Decimal('5000.00')
        subscription.save()

        # Mock YooKassa API
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')
        mock_yookassa.return_value = {
            'id': 'test-payment-id',
            'status': 'pending',
            'confirmation': {
                'confirmation_url': 'https://test.url'
            }
        }

        # Act
        call_command('process_subscription_payments')

        # Assert
        # Проверяем что создан Payment
        payment = Payment.objects.filter(
            metadata__subscription_id=subscription.id
        ).first()
        assert payment is not None

        # Проверяем что создан SubjectPayment
        subject_payment = SubjectPayment.objects.filter(
            enrollment=enrollment,
            payment=payment
        ).first()
        assert subject_payment is not None
        assert subject_payment.amount == Decimal('5000.00')
        assert subject_payment.status == SubjectPayment.Status.WAITING_FOR_PAYMENT


@pytest.mark.unit
@pytest.mark.recurring_payments
class TestPaymentMethodIdInMetadata:
    """Тесты для корректного сохранения payment_method_id в metadata"""

    def test_payment_metadata_contains_payment_method_id(
        self,
        subscription,
        student_with_parent,
        mocker
    ):
        """Тест: metadata платежа содержит payment_method_id"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.payment_method_id = 'pm_test_payment_method_123'
        subscription.save()

        # Mock YooKassa API
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')
        mock_yookassa.return_value = {
            'id': 'test-payment-id',
            'status': 'pending',
            'confirmation': {
                'confirmation_url': 'https://test.url'
            }
        }

        # Act
        call_command('process_subscription_payments')

        # Assert
        payment = Payment.objects.filter(
            metadata__subscription_id=subscription.id
        ).first()

        assert payment is not None
        assert payment.metadata['payment_method_id'] == 'pm_test_payment_method_123'
        assert payment.metadata['is_recurring'] is True
        assert payment.metadata['create_subscription'] is False

    def test_first_payment_without_payment_method_id(
        self,
        enrollment,
        payment
    ):
        """Тест: первый платеж создается БЕЗ payment_method_id в metadata"""
        # Arrange
        from materials.parent_dashboard_service import ParentDashboardService

        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Создаем первый платеж (без рекурсии)
        # Mock request
        from django.test import RequestFactory
        factory = RequestFactory()
        fake_request = factory.get('/')
        fake_request.META['HTTP_HOST'] = 'localhost'

        # Mock create_yookassa_payment
        import unittest.mock as mock
        with mock.patch('payments.views.create_yookassa_payment') as mock_yookassa:
            mock_yookassa.return_value = {
                'id': 'test-payment-id',
                'status': 'pending',
                'confirmation': {
                    'confirmation_url': 'https://test.url',
                    'return_url': 'https://test.url/return'
                }
            }

            # Act
            result = service.initiate_payment(
                child=enrollment.student,
                enrollment=enrollment,
                amount=Decimal('5000.00'),
                create_subscription=True,
                request=fake_request
            )

        # Assert
        created_payment = Payment.objects.filter(
            metadata__enrollment_id=enrollment.id
        ).first()

        assert created_payment is not None
        # Первый платеж НЕ содержит payment_method_id (он будет сохранен после webhook)
        assert 'payment_method_id' not in created_payment.metadata or created_payment.metadata.get('payment_method_id') is None
        assert created_payment.metadata['create_subscription'] is True
