"""
Сервис для обработки платежей и подписок
Централизованная логика для предотвращения дублирования кода
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.conf import settings

logger = logging.getLogger(__name__)


def process_successful_payment(payment):
    """
    Централизованная обработка успешно оплаченного платежа.

    Выполняет:
    1. Обновление статуса Payment → SUCCEEDED
    2. Синхронизация статусов SubjectPayment → PAID
    3. Активация enrollment
    4. Создание/обновление подписки (если требуется)
    5. Отправка уведомлений родителю

    Args:
        payment: Объект Payment который был успешно оплачен

    Returns:
        dict: Результат обработки {
            'success': bool,
            'subject_payments_updated': int,
            'enrollments_activated': int,
            'subscriptions_processed': int,
            'notifications_sent': int,
            'errors': list
        }
    """
    from payments.models import Payment
    from materials.models import SubjectPayment as SP, SubjectSubscription
    from notifications.notification_service import NotificationService

    result = {
        'success': True,
        'subject_payments_updated': 0,
        'enrollments_activated': 0,
        'subscriptions_processed': 0,
        'notifications_sent': 0,
        'errors': []
    }

    logger.info(f"=== Starting process_successful_payment for payment {payment.id} ===")
    logger.info(f"Payment metadata: {payment.metadata}")
    logger.info(f"Payment current status: {payment.status}")

    try:
        with transaction.atomic():
            # 1. Обновляем статус Payment (если еще не обновлен)
            if payment.status != Payment.Status.SUCCEEDED:
                payment.status = Payment.Status.SUCCEEDED
                payment.paid_at = timezone.now()
                payment.save(update_fields=['status', 'paid_at', 'updated'])
                logger.info(f"Payment {payment.id} marked as succeeded. Metadata: {payment.metadata}")

            # 2. Получаем все связанные SubjectPayment
            subject_payments = SP.objects.filter(payment=payment).select_related(
                'enrollment',
                'enrollment__student',
                'enrollment__student__student_profile',
                'enrollment__subject'
            )

            logger.info(f"Found {subject_payments.count()} subject payments for payment {payment.id}")

            for subject_payment in subject_payments:
                try:
                    # 2.1. Обновляем статус SubjectPayment
                    if subject_payment.status != SP.Status.PAID:
                        subject_payment.status = SP.Status.PAID
                        subject_payment.paid_at = payment.paid_at
                        subject_payment.save(update_fields=['status', 'paid_at', 'updated_at'])
                        result['subject_payments_updated'] += 1
                        logger.info(f"SubjectPayment {subject_payment.id} marked as PAID")

                    # 2.2. Активируем enrollment
                    enrollment = subject_payment.enrollment
                    logger.info(f"Enrollment {enrollment.id} BEFORE activation: is_active={enrollment.is_active}")
                    if not enrollment.is_active:
                        enrollment.is_active = True
                        enrollment.save(update_fields=['is_active'])
                        result['enrollments_activated'] += 1
                        logger.info(f"Activated enrollment {enrollment.id} after payment {payment.id}")
                        logger.info(f"Enrollment {enrollment.id} AFTER activation: is_active={enrollment.is_active}")
                        logger.info(f"Enrollment activation saved to database")

                    # 2.3. Обрабатываем подписку (если требуется)
                    subscription_processed = _process_subscription_for_payment(
                        payment,
                        subject_payment,
                        enrollment
                    )
                    if subscription_processed:
                        result['subscriptions_processed'] += 1
                        logger.info(f"Subscription processed successfully for enrollment {enrollment.id}")
                    else:
                        logger.warning(f"Subscription NOT processed for enrollment {enrollment.id}")

                    # 2.4. Отправляем уведомление родителю
                    notification_sent = _send_payment_notification(subject_payment)
                    if notification_sent:
                        result['notifications_sent'] += 1

                except Exception as sp_error:
                    error_msg = f"Error processing SubjectPayment {subject_payment.id}: {sp_error}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)
                    # Не прерываем обработку других subject_payments

    except Exception as e:
        error_msg = f"Critical error in process_successful_payment for payment {payment.id}: {e}"
        logger.error(error_msg, exc_info=True)
        result['success'] = False
        result['errors'].append(error_msg)

    logger.info(f"=== Completed process_successful_payment for payment {payment.id} ===")
    logger.info(f"Result: {result}")
    return result


def _process_subscription_for_payment(payment, subject_payment, enrollment):
    """
    Создает или обновляет подписку после успешной оплаты.

    Args:
        payment: Объект Payment
        subject_payment: Объект SubjectPayment
        enrollment: Объект SubjectEnrollment

    Returns:
        bool: True если подписка была обработана
    """
    from materials.models import SubjectSubscription

    # Проверяем метаданные платежа
    create_subscription = payment.metadata.get('create_subscription', False) if isinstance(payment.metadata, dict) else False
    is_recurring = payment.metadata.get('is_recurring', False) if isinstance(payment.metadata, dict) else False

    logger.info(
        f"SubjectPayment {subject_payment.id}: "
        f"create_subscription={create_subscription}, is_recurring={is_recurring}"
    )

    # Если не требуется обработка подписки - выходим
    if not (create_subscription or is_recurring):
        return False

    try:
        # Определяем интервал следующего платежа в зависимости от режима
        if settings.PAYMENT_DEVELOPMENT_MODE:
            next_payment_delta = timedelta(minutes=settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES)
            payment_interval_weeks = 0  # Не используется в режиме разработки
        else:
            next_payment_delta = timedelta(weeks=settings.PRODUCTION_RECURRING_INTERVAL_WEEKS)
            payment_interval_weeks = settings.PRODUCTION_RECURRING_INTERVAL_WEEKS

        # Проверяем, существует ли уже подписка для этого enrollment
        try:
            subscription = SubjectSubscription.objects.get(enrollment=enrollment)
            # Если подписка существует, обновляем её
            old_amount = subscription.amount
            subscription.amount = subject_payment.amount
            subscription.status = SubjectSubscription.Status.ACTIVE
            # Планируем следующий платеж после успешной оплаты
            subscription.next_payment_date = timezone.now() + next_payment_delta
            subscription.payment_interval_weeks = payment_interval_weeks
            subscription.cancelled_at = None  # Сбрасываем дату отмены, если была
            subscription.save()
            logger.info(
                f"Updated existing subscription {subscription.id} for enrollment {enrollment.id} "
                f"(amount: {old_amount} -> {subject_payment.amount}, "
                f"next_payment: {subscription.next_payment_date})"
            )
            return True

        except SubjectSubscription.DoesNotExist:
            # Если подписки нет и это новый платеж с create_subscription, создаём новую
            if create_subscription:
                subscription = SubjectSubscription.objects.create(
                    enrollment=enrollment,
                    amount=subject_payment.amount,
                    status=SubjectSubscription.Status.ACTIVE,
                    next_payment_date=timezone.now() + next_payment_delta,
                    payment_interval_weeks=payment_interval_weeks
                )
                logger.info(
                    f"Created new subscription {subscription.id} for enrollment {enrollment.id} "
                    f"after successful payment (next_payment: {subscription.next_payment_date})"
                )
                return True
            else:
                logger.warning(
                    f"Recurring payment {payment.id} for enrollment {enrollment.id} "
                    f"but subscription not found"
                )
                return False

    except Exception as e:
        logger.error(
            f"Failed to create/update subscription after payment {payment.id}: {e}",
            exc_info=True
        )
        return False


def _send_payment_notification(subject_payment):
    """
    Отправляет уведомление родителю об успешной оплате.

    Args:
        subject_payment: Объект SubjectPayment

    Returns:
        bool: True если уведомление отправлено успешно
    """
    from notifications.notification_service import NotificationService

    try:
        student = subject_payment.enrollment.student
        parent = getattr(student.student_profile, 'parent', None) if hasattr(student, 'student_profile') else None

        if parent:
            NotificationService().notify_payment_processed(
                parent=parent,
                status='paid',
                amount=str(subject_payment.amount),
                enrollment_id=subject_payment.enrollment.id,
            )
            logger.info(f"Sent payment notification to parent {parent.id} for payment {subject_payment.payment.id}")
            return True
        else:
            logger.warning(f"No parent found for student {student.id}, skipping notification")
            return False

    except Exception as e:
        logger.error(f"Error sending payment notification: {e}", exc_info=True)
        return False


def sync_payment_status(payment, yookassa_payment_data):
    """
    Синхронизирует статус платежа с данными от YooKassa.

    Args:
        payment: Объект Payment
        yookassa_payment_data: dict с данными от YooKassa API

    Returns:
        tuple: (status_changed: bool, old_status: str, new_status: str)
    """
    from payments.models import Payment

    yookassa_status = yookassa_payment_data.get('status')
    old_status = payment.status
    status_changed = False

    # Маппинг статусов YooKassa → Payment
    status_mapping = {
        'pending': Payment.Status.PENDING,
        'waiting_for_capture': Payment.Status.WAITING_FOR_CAPTURE,
        'succeeded': Payment.Status.SUCCEEDED,
        'canceled': Payment.Status.CANCELED,
        'failed': Payment.Status.FAILED,
    }

    new_status = status_mapping.get(yookassa_status)

    if new_status and payment.status != new_status:
        payment.status = new_status

        # Устанавливаем paid_at для успешных платежей
        if new_status == Payment.Status.SUCCEEDED and not payment.paid_at:
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at', 'updated'])
        else:
            payment.save(update_fields=['status', 'updated'])

        status_changed = True
        logger.info(f"Payment {payment.id} status changed: {old_status} → {new_status}")

    return status_changed, old_status, new_status
