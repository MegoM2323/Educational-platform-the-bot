"""
Tests for payments.services module
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from payments.models import Payment
from payments.services import process_successful_payment
from materials.models import SubjectPayment, SubjectSubscription


@pytest.mark.unit
@pytest.mark.payment
class TestProcessSuccessfulPayment:
    """Tests for process_successful_payment function"""

    def test_successful_payment_processing(self, payment, subject_payment):
        """Test basic successful payment processing"""
        # Arrange
        payment.status = Payment.Status.PENDING
        payment.metadata = {'test': True}
        payment.save()

        # Make enrollment inactive to test activation
        subject_payment.enrollment.is_active = False
        subject_payment.enrollment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        assert result['subject_payments_updated'] == 1
        assert result['enrollments_activated'] == 1

        # Check payment status
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED
        assert payment.paid_at is not None

        # Check subject payment status
        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.PAID
        assert subject_payment.paid_at == payment.paid_at

        # Check enrollment activated
        assert subject_payment.enrollment.is_active is True

    def test_idempotency_already_succeeded(self, payment, subject_payment):
        """Test that already processed payment is handled correctly (idempotency)"""
        # Arrange
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save()

        subject_payment.status = SubjectPayment.Status.PAID
        subject_payment.paid_at = payment.paid_at
        subject_payment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        # No updates should happen since already processed
        assert result['subject_payments_updated'] == 0

    def test_creates_subscription_with_flag(self, payment, subject_payment):
        """Test that subscription is created when create_subscription=True"""
        # Arrange
        payment.status = Payment.Status.PENDING
        payment.metadata = {
            'create_subscription': True,
            'is_recurring': False
        }
        payment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        assert result['subscriptions_processed'] == 1

        # Check subscription created
        subscription = SubjectSubscription.objects.get(
            enrollment=subject_payment.enrollment
        )
        assert subscription.status == SubjectSubscription.Status.ACTIVE
        assert subscription.amount == subject_payment.amount
        assert subscription.next_payment_date > timezone.now()

    def test_updates_existing_subscription_on_recurring(self, payment, subject_payment, subscription):
        """Test that existing subscription is updated on recurring payment"""
        # Arrange
        old_amount = subscription.amount

        # Set old_next_payment to past so new one will be in future
        subscription.next_payment_date = timezone.now() - timedelta(days=1)
        subscription.save()
        old_next_payment = subscription.next_payment_date

        payment.status = Payment.Status.PENDING
        payment.amount = Decimal('200.00')
        payment.metadata = {
            'create_subscription': False,
            'is_recurring': True
        }
        payment.save()

        subject_payment.amount = payment.amount
        subject_payment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        assert result['subscriptions_processed'] == 1

        # Check subscription updated
        subscription.refresh_from_db()
        assert subscription.status == SubjectSubscription.Status.ACTIVE
        assert subscription.amount == Decimal('200.00')
        assert subscription.amount != old_amount
        assert subscription.next_payment_date > old_next_payment
        assert subscription.next_payment_date > timezone.now()

    def test_activates_inactive_enrollment(self, payment, subject_payment):
        """Test that inactive enrollment is activated"""
        # Arrange
        enrollment = subject_payment.enrollment
        enrollment.is_active = False
        enrollment.save()

        payment.status = Payment.Status.PENDING
        payment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        assert result['enrollments_activated'] == 1

        enrollment.refresh_from_db()
        assert enrollment.is_active is True

    def test_handles_payment_without_subject_payment(self, payment):
        """Test graceful handling when payment has no associated subject_payment"""
        # Arrange
        payment.status = Payment.Status.PENDING
        payment.save()

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        assert result['subject_payments_updated'] == 0
        assert result['enrollments_activated'] == 0
        assert result['subscriptions_processed'] == 0

    def test_transaction_rollback_on_error(self, payment, subject_payment, mocker):
        """Test that transaction is rolled back on error"""
        # Arrange
        payment.status = Payment.Status.PENDING
        payment.save()

        # Mock to raise exception during processing
        mocker.patch(
            'payments.services._send_payment_notification',
            side_effect=Exception('Test error')
        )

        # Act
        result = process_successful_payment(payment)

        # Assert
        # Payment should still be updated despite notification error
        assert result['success'] is True
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED

    def test_sets_paid_at_timestamp(self, payment, subject_payment):
        """Test that paid_at timestamp is set correctly"""
        # Arrange
        before_payment = timezone.now()
        payment.status = Payment.Status.PENDING
        payment.save()

        # Act
        result = process_successful_payment(payment)
        after_payment = timezone.now()

        # Assert
        assert result['success'] is True

        payment.refresh_from_db()
        subject_payment.refresh_from_db()

        assert payment.paid_at is not None
        assert before_payment <= payment.paid_at <= after_payment
        assert subject_payment.paid_at == payment.paid_at


@pytest.mark.integration
@pytest.mark.payment
class TestProcessSuccessfulPaymentIntegration:
    """Integration tests for process_successful_payment with full flow"""

    def test_full_payment_flow_with_subscription(
        self,
        student_with_parent,
        subject,
        teacher_user
    ):
        """Test complete payment flow from creation to subscription"""
        # Arrange
        from materials.models import SubjectEnrollment

        enrollment = SubjectEnrollment.objects.create(
            student=student_with_parent,
            subject=subject,
            teacher=teacher_user,
            is_active=False  # Initially inactive
        )

        payment = Payment.objects.create(
            amount=Decimal('100.00'),
            service_name="Test payment",
            customer_fio="Test User",
            description="Test",
            status=Payment.Status.PENDING,
            metadata={
                'create_subscription': True,
                'enrollment_id': enrollment.id
            }
        )

        subject_payment = SubjectPayment.objects.create(
            enrollment=enrollment,
            payment=payment,
            amount=payment.amount,
            status=SubjectPayment.Status.PENDING,
            due_date=timezone.now() + timedelta(days=7)
        )

        # Act
        result = process_successful_payment(payment)

        # Assert
        assert result['success'] is True
        assert result['subject_payments_updated'] == 1
        assert result['enrollments_activated'] == 1
        assert result['subscriptions_processed'] == 1

        # Verify all components
        payment.refresh_from_db()
        assert payment.status == Payment.Status.SUCCEEDED

        subject_payment.refresh_from_db()
        assert subject_payment.status == SubjectPayment.Status.PAID

        enrollment.refresh_from_db()
        assert enrollment.is_active is True

        subscription = SubjectSubscription.objects.get(enrollment=enrollment)
        assert subscription.status == SubjectSubscription.Status.ACTIVE
        assert subscription.amount == Decimal('100.00')
