"""
Tests for process_subscription_payments management command
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
@pytest.mark.subscription
class TestProcessSubscriptionPaymentsCommand:
    """Tests for process_subscription_payments management command"""

    def test_creates_payment_for_due_subscription(
        self,
        subscription,
        student_with_parent,
        mocker
    ):
        """Test that payment is created for subscription with due date"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
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
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Найдено 1 подписок для обработки' in output
        assert 'обработано 1' in output

        # Check payment created
        payments = Payment.objects.filter(
            metadata__subscription_id=subscription.id
        )
        assert payments.count() == 1

        payment = payments.first()
        assert payment.amount == subscription.amount
        assert payment.status == Payment.Status.PENDING

    def test_updates_next_payment_date_immediately(
        self,
        subscription,
        student_with_parent,
        mocker
    ):
        """Test that next_payment_date is updated immediately to prevent spam"""
        # Arrange
        old_next_payment = timezone.now() - timedelta(minutes=1)
        subscription.next_payment_date = old_next_payment
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

        # next_payment_date should be updated to future
        assert subscription.next_payment_date > timezone.now()
        assert subscription.next_payment_date > old_next_payment

    def test_skips_subscription_with_pending_payment(
        self,
        subscription,
        student_with_parent,
        enrollment,
        mocker
    ):
        """Test that subscription is skipped if pending payment exists"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.save()

        # Create existing pending payment
        existing_payment = Payment.objects.create(
            amount=Decimal('100.00'),
            service_name="Test",
            customer_fio="Test",
            description="Test",
            status=Payment.Status.PENDING
        )

        SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=existing_payment,
            amount=existing_payment.amount,
            status=SubjectPayment.Status.PENDING,
            due_date=timezone.now() + timedelta(days=7)
        )

        # Mock YooKassa API
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')

        # Act
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'уже есть необработанный платеж' in output

        # Verify no new payment created
        mock_yookassa.assert_not_called()

        # Verify next_payment_date NOT updated (subscription skipped)
        subscription.refresh_from_db()
        assert subscription.next_payment_date < timezone.now()

    def test_skips_subscription_without_parent(
        self,
        subscription,
        student_user,  # Student without parent
        mocker
    ):
        """Test that subscription is skipped if student has no parent"""
        # Arrange
        # Переназначаем студента на student_user без родителя
        subscription.enrollment.student = student_user
        subscription.enrollment.save()

        # Убеждаемся что у student_user нет родителя
        if hasattr(student_user, 'student_profile') and student_user.student_profile:
            student_user.student_profile.parent = None
            student_user.student_profile.save()

        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.save()

        # Mock YooKassa API - should return dict, not Mock object
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')
        mock_yookassa.return_value = {
            'id': 'test-payment-id',
            'status': 'pending',
            'confirmation': {
                'confirmation_url': 'https://test.url'
            }
        }

        # Act
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'нет родителя' in output

        # Verify no payment created
        mock_yookassa.assert_not_called()

    def test_dry_run_mode(self, subscription, student_with_parent):
        """Test dry-run mode doesn't create actual payments"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.save()

        payments_before = Payment.objects.count()

        # Act
        out = StringIO()
        call_command('process_subscription_payments', '--dry-run', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Режим тестирования (dry-run)' in output
        assert '[DRY-RUN]' in output

        # No payments created
        payments_after = Payment.objects.count()
        assert payments_before == payments_after

    def test_uses_development_mode_settings(
        self,
        subscription,
        student_with_parent,
        settings,
        mocker
    ):
        """Test that development mode settings are used correctly"""
        # Arrange
        settings.PAYMENT_DEVELOPMENT_MODE = True
        settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES = 15

        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
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

        # Next payment should be 15 minutes in future
        expected_next = timezone.now() + timedelta(minutes=15)
        time_diff = abs((subscription.next_payment_date - expected_next).total_seconds())

        # Allow 5 seconds tolerance for execution time
        assert time_diff < 5

        # payment_interval_weeks should be 0 for development mode
        assert subscription.payment_interval_weeks == 0

    def test_handles_yookassa_api_error(
        self,
        subscription,
        student_with_parent,
        mocker
    ):
        """Test graceful handling of YooKassa API errors"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.save()

        # Mock YooKassa API to return None (error)
        mock_yookassa = mocker.patch('payments.views.create_yookassa_payment')
        mock_yookassa.return_value = None

        # Act
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Ошибка при обработке подписки' in output or 'ошибок 1' in output

        # Payment should not exist
        payments = Payment.objects.filter(
            metadata__subscription_id=subscription.id
        )
        assert payments.count() == 0

    def test_processes_multiple_subscriptions(
        self,
        subscription,
        student_with_parent,
        subject,
        teacher_user,
        mocker
    ):
        """Test processing multiple subscriptions in single run"""
        # Arrange
        subscription.next_payment_date = timezone.now() - timedelta(minutes=1)
        subscription.save()

        # Create second student and subscription
        from materials.models import SubjectEnrollment, SubjectSubscription

        student2 = student_with_parent.__class__.objects.create(
            username='student2',
            email='student2@test.com',
            role=student_with_parent.role,
            first_name='Student2',
            last_name='Test'
        )

        from accounts.models import StudentProfile, ParentProfile

        parent2 = student_with_parent.__class__.objects.create(
            username='parent2',
            email='parent2@test.com',
            role='parent',
            first_name='Parent2',
            last_name='Test'
        )

        ParentProfile.objects.create(user=parent2)
        student_profile2 = StudentProfile.objects.create(user=student2)
        student_profile2.parent = parent2
        student_profile2.save()

        enrollment2 = SubjectEnrollment.objects.create(
            student=student2,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        subscription2 = SubjectSubscription.objects.create(
            enrollment=enrollment2,
            amount=Decimal('200.00'),
            status=SubjectSubscription.Status.ACTIVE,
            next_payment_date=timezone.now() - timedelta(minutes=1),
            payment_interval_weeks=1
        )

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
        out = StringIO()
        call_command('process_subscription_payments', stdout=out)

        # Assert
        output = out.getvalue()
        assert 'Найдено 2 подписок для обработки' in output
        assert 'обработано 2' in output

        # Both payments created
        assert Payment.objects.count() == 2
