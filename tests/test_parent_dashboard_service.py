"""
Тесты для ParentDashboardService с фокусом на исправленные методы
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from materials.models import SubjectPayment, SubjectSubscription, SubjectEnrollment
from materials.parent_dashboard_service import ParentDashboardService
from payments.models import Payment


@pytest.mark.unit
@pytest.mark.parent_dashboard
class TestGetSubjectPaymentInfo:
    """Тесты для метода get_subject_payment_info()"""

    def test_payment_info_with_active_subscription(
        self,
        enrollment,
        subscription,
        subject_payment
    ):
        """Тест: информация о платеже с активной подпиской"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Устанавливаем активную подписку
        subscription.status = SubjectSubscription.Status.ACTIVE
        subscription.next_payment_date = timezone.now() + timedelta(days=7)
        subscription.save()

        # Устанавливаем оплаченный платеж
        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.paid_at = timezone.now()
        subject_payment.amount = Decimal('5000.00')
        subject_payment.save()

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert
        assert result['payment_status'] == 'paid'
        assert result['has_subscription'] is True
        assert result['next_payment_date'] is not None
        assert result['amount'] == '5000.00'
        assert result['last_payment_date'] is not None

    def test_payment_info_without_subscription(
        self,
        enrollment,
        subject_payment
    ):
        """Тест: информация о платеже без подписки"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Устанавливаем оплаченный платеж БЕЗ подписки
        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.paid_at = timezone.now()
        subject_payment.save()

        # Убедимся что нет подписки
        SubjectSubscription.objects.filter(enrollment=enrollment).delete()

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert
        assert result['payment_status'] == 'paid'
        assert result['has_subscription'] is False
        assert result['next_payment_date'] is None

    def test_payment_info_pending_status(
        self,
        enrollment,
        payment,
        subscription
    ):
        """Тест: информация о платеже в статусе PENDING"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Создаем платеж в статусе PENDING с будущей due_date
        future_due_date = timezone.now() + timedelta(days=3)
        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('5000.00'),
            status=SubjectPayment.Status.PENDING,
            due_date=future_due_date
        )

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert
        assert result['payment_status'] == 'pending'
        assert result['amount'] == '5000.00'
        assert result['due_date'] is not None

    def test_payment_info_overdue_status(
        self,
        enrollment,
        payment
    ):
        """Тест: информация о платеже в статусе OVERDUE (просрочен)"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Создаем платеж в статусе PENDING с прошедшей due_date
        past_due_date = timezone.now() - timedelta(days=2)
        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('5000.00'),
            status=SubjectPayment.Status.PENDING,
            due_date=past_due_date
        )

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert
        assert result['payment_status'] == 'overdue'

    def test_payment_info_waiting_for_payment_status(
        self,
        enrollment,
        payment
    ):
        """Тест: информация о платеже в статусе WAITING_FOR_PAYMENT"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Создаем платеж в статусе WAITING_FOR_PAYMENT
        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=Decimal('5000.00'),
            status=SubjectPayment.Status.WAITING_FOR_PAYMENT,
            due_date=timezone.now() + timedelta(days=7)
        )

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert
        assert result['payment_status'] == 'waiting_for_payment'

    def test_payment_info_no_payment_exists(
        self,
        enrollment
    ):
        """Тест: информация когда платежей нет вообще"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Убедимся что нет платежей
        SubjectPayment.objects.filter(enrollment=enrollment).delete()

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert
        assert result['payment_status'] == 'no_payment'
        assert result['has_subscription'] is False
        assert result['amount'] == '0.00'
        assert result['last_payment_date'] is None

    def test_payment_info_multiple_payments_returns_latest(
        self,
        enrollment,
        subscription
    ):
        """Тест: возвращается информация о последнем платеже"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Создаем несколько платежей
        payment1 = Payment.objects.create(
            amount=Decimal('100.00'),
            service_name="Test 1",
            customer_fio="Test",
            description="Test"
        )
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment1,
            amount=Decimal('100.00'),
            status=SubjectPayment.Status.PAID,
            paid_at=timezone.now() - timedelta(days=14)
        )

        payment2 = Payment.objects.create(
            amount=Decimal('200.00'),
            service_name="Test 2",
            customer_fio="Test",
            description="Test"
        )
        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment2,
            amount=Decimal('200.00'),
            status=SubjectPayment.Status.PAID,
            paid_at=timezone.now() - timedelta(days=7)
        )

        # Act
        result = service.get_subject_payment_info(enrollment)

        # Assert - должен вернуться последний (payment2)
        assert result['amount'] == '200.00'


@pytest.mark.unit
@pytest.mark.parent_dashboard
class TestGetDashboardData:
    """Тесты для метода get_dashboard_data() с новыми полями"""

    def test_dashboard_includes_subscription_info(
        self,
        enrollment,
        subscription,
        subject_payment
    ):
        """Тест: dashboard включает информацию о подписке"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Настраиваем подписку
        subscription.status = SubjectSubscription.Status.ACTIVE
        subscription.next_payment_date = timezone.now() + timedelta(days=7)
        subscription.amount = Decimal('5000.00')
        subscription.save()

        # Настраиваем платеж
        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.paid_at = timezone.now()
        subject_payment.amount = Decimal('5000.00')
        subject_payment.save()

        # Act
        result = service.get_dashboard_data()

        # Assert
        assert len(result['children']) > 0
        child_data = result['children'][0]
        assert len(child_data['subjects']) > 0

        subject_info = child_data['subjects'][0]
        assert subject_info['payment_status'] == 'paid'
        assert subject_info['has_subscription'] is True
        assert subject_info['next_payment_date'] is not None
        assert subject_info['amount'] == '5000.00'

    def test_dashboard_payment_statistics(
        self,
        enrollment,
        subscription,
        subject_payment
    ):
        """Тест: статистика платежей в dashboard"""
        # Arrange
        parent = enrollment.student.student_profile.parent
        service = ParentDashboardService(parent_user=parent)

        # Настраиваем оплаченный платеж
        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.save()

        # Act
        result = service.get_dashboard_data()

        # Assert
        stats = result['statistics']
        assert stats['completed_payments'] >= 1
        assert stats['pending_payments'] >= 0
        assert stats['overdue_payments'] >= 0
