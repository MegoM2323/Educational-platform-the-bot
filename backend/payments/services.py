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
    5. Отправка уведомлений родителю (ПОСЛЕ транзакции)

    ВАЖНО: Уведомления отправляются ВНЕ транзакции, чтобы ошибки нотификаций
    не приводили к откату критических операций (оплата, активация enrollment).

    CRITICAL FIX #7: Если NotificationService упадет внутри транзакции,
    все изменения откатятся (Payment.status → PENDING, enrollment.is_active → False).
    Решение: собрать список уведомлений внутри транзакции, отправить ПОСЛЕ commit.

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

    result = {
        'success': True,
        'subject_payments_updated': 0,
        'enrollments_activated': 0,
        'subscriptions_processed': 0,
        'notifications_sent': 0,
        'errors': []
    }

    # Список уведомлений для отправки ПОСЛЕ транзакции
    notifications_to_send = []

    logger.info(f"=== Starting process_successful_payment for payment {payment.id} ===")
    logger.info(f"Payment metadata: {payment.metadata}")
    logger.info(f"Payment current status: {payment.status}")

    try:
        logger.info(f"[Transaction START] Beginning atomic transaction for payment {payment.id}")

        with transaction.atomic():
            # 1. Обновляем статус Payment (если еще не обновлен)
            if payment.status != Payment.Status.SUCCEEDED:
                payment.status = Payment.Status.SUCCEEDED
                payment.paid_at = timezone.now()
                payment.save(update_fields=['status', 'paid_at', 'updated'])

                # ✅ Verify Payment status saved
                payment.refresh_from_db()
                if payment.status == Payment.Status.SUCCEEDED:
                    logger.info(f"✅ VERIFIED: Payment {payment.id} status=SUCCEEDED in DB. Metadata: {payment.metadata}")
                else:
                    error_msg = (
                        f"CRITICAL: Failed to update Payment {payment.id} status - "
                        f"save() completed but status is {payment.status} instead of SUCCEEDED"
                    )
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    raise Exception(error_msg)

            # 2. Получаем все связанные SubjectPayment
            subject_payments = SP.objects.filter(payment=payment).select_related(
                'enrollment',
                'enrollment__student',
                'enrollment__student__student_profile',
                'enrollment__subject'
            )

            logger.info(f"Found {subject_payments.count()} subject payments for payment {payment.id}")

            # 2.0 КРИТИЧНО: Обработка orphaned payments (платежей без SubjectPayment)
            # Это может произойти если webhook придет раньше чем создается SubjectPayment
            # ПРИМЕЧАНИЕ: С исправлением race condition в parent_dashboard_service.py (создание SubjectPayment
            # ДО вызова YooKassa API), этот код должен быть вызван только в исключительных случаях
            if subject_payments.count() == 0 and isinstance(payment.metadata, dict):
                logger.warning(
                    f"⚠️ ORPHAN PAYMENT DETECTED: Payment {payment.id} has no SubjectPayment! "
                    f"This should NOT happen after race condition fix. Investigating metadata..."
                )
                enrollment_id = payment.metadata.get('enrollment_id')
                if enrollment_id:
                    try:
                        from materials.models import SubjectEnrollment
                        enrollment = SubjectEnrollment.objects.get(id=enrollment_id)

                        # Создаем недостающий SubjectPayment
                        subject_payment = SP.objects.create(
                            enrollment=enrollment,
                            payment=payment,
                            amount=payment.amount,
                            status=SP.Status.PENDING
                        )
                        logger.warning(
                            f"⚠️ ORPHAN RECOVERY: Created SubjectPayment {subject_payment.id} for payment {payment.id} "
                            f"from metadata (enrollment_id={enrollment_id}). This indicates race condition still occurring!"
                        )
                        subject_payments = [subject_payment]

                    except SubjectEnrollment.DoesNotExist:
                        logger.error(f"Enrollment {enrollment_id} not found in metadata for orphaned payment {payment.id}")
                        result['errors'].append(f"Enrollment {enrollment_id} not found for orphaned payment")
                        return result
                    except Exception as e:
                        logger.error(f"Failed to create orphaned SubjectPayment for payment {payment.id}: {e}", exc_info=True)
                        result['errors'].append(f"Failed to create orphaned SubjectPayment: {e}")
                        return result
                else:
                    logger.error(f"No enrollment_id in metadata for orphaned payment {payment.id}. Metadata: {payment.metadata}")
                    result['errors'].append("No enrollment_id found in payment metadata for orphaned payment")
                    return result

            for subject_payment in subject_payments:
                try:
                    # 2.1. Обновляем статус SubjectPayment
                    if subject_payment.status != SP.Status.PAID:
                        subject_payment.status = SP.Status.PAID
                        subject_payment.paid_at = payment.paid_at
                        subject_payment.save(update_fields=['status', 'paid_at', 'updated_at'])

                        # ✅ Verify SubjectPayment status saved
                        subject_payment.refresh_from_db()
                        if subject_payment.status == SP.Status.PAID:
                            result['subject_payments_updated'] += 1
                            logger.info(f"✅ VERIFIED: SubjectPayment {subject_payment.id} status=PAID in DB")
                        else:
                            error_msg = (
                                f"CRITICAL: Failed to update SubjectPayment {subject_payment.id} status - "
                                f"save() completed but status is {subject_payment.status} instead of PAID"
                            )
                            logger.error(error_msg)
                            result['errors'].append(error_msg)
                            raise Exception(error_msg)

                    # 2.2. Активируем enrollment
                    enrollment = subject_payment.enrollment
                    logger.info(f"Enrollment {enrollment.id} BEFORE activation: is_active={enrollment.is_active}")
                    if not enrollment.is_active:
                        enrollment.is_active = True
                        enrollment.save(update_fields=['is_active'])

                        # ✅ CRITICAL: Verify the save actually persisted to database
                        enrollment.refresh_from_db()

                        if enrollment.is_active:
                            result['enrollments_activated'] += 1
                            logger.info(f"✅ VERIFIED: Enrollment {enrollment.id} is_active=True in DB after payment {payment.id}")
                        else:
                            # ⚠️ Save completed but is_active is still False - database write failed!
                            error_msg = (
                                f"CRITICAL: Failed to activate enrollment {enrollment.id} - "
                                f"save() completed but is_active still False in database. "
                                f"This may indicate connection issues or transaction problems."
                            )
                            logger.error(error_msg)
                            result['errors'].append(error_msg)
                            raise Exception(error_msg)  # Rollback transaction

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

                    # 2.4. Сохраняем информацию для отправки уведомления (БЕЗ отправки)
                    # Уведомления будут отправлены ПОСЛЕ успешного завершения транзакции
                    notifications_to_send.append(subject_payment)
                    logger.info(f"Added notification to queue for SubjectPayment {subject_payment.id}")

                except Exception as sp_error:
                    error_msg = f"Error processing SubjectPayment {subject_payment.id}: {sp_error}"
                    logger.error(error_msg, exc_info=True)
                    result['errors'].append(error_msg)
                    # Не прерываем обработку других subject_payments

        logger.info(f"[Transaction COMMITTED] All database changes committed for payment {payment.id}")

    except Exception as e:
        error_msg = f"Critical error in process_successful_payment for payment {payment.id}: {e}"
        logger.error(error_msg, exc_info=True)
        logger.info(f"[Transaction ROLLBACK] Transaction rolled back due to error")
        result['success'] = False
        result['errors'].append(error_msg)

    # КРИТИЧНО: Отправка уведомлений ПОСЛЕ транзакции
    # Если уведомление упадет, платеж всё равно будет обработан
    if result['success'] and notifications_to_send:
        logger.info(f"[Notifications] Starting notification sending for {len(notifications_to_send)} payments (outside transaction)")

        for subject_payment in notifications_to_send:
            try:
                notification_sent = _send_payment_notification(subject_payment)
                if notification_sent:
                    result['notifications_sent'] += 1
                    logger.info(f"[Notifications] Successfully sent notification for SubjectPayment {subject_payment.id}")
                else:
                    logger.warning(f"[Notifications] Failed to send notification for SubjectPayment {subject_payment.id} (non-critical)")
            except Exception as notification_error:
                # Ошибки уведомлений не критичны - логируем, но не добавляем в errors
                logger.error(
                    f"[Notifications] Non-critical error sending notification for SubjectPayment {subject_payment.id}: "
                    f"{notification_error}",
                    exc_info=True
                )
                # НЕ добавляем в result['errors'] - платеж уже обработан успешно

        logger.info(f"[Notifications] Completed notification sending. Sent: {result['notifications_sent']}/{len(notifications_to_send)}")

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

            # ✅ Verify subscription update saved
            subscription.refresh_from_db()
            if subscription.status == SubjectSubscription.Status.ACTIVE and subscription.amount == subject_payment.amount:
                logger.info(
                    f"✅ VERIFIED: Updated subscription {subscription.id} for enrollment {enrollment.id} "
                    f"(amount: {old_amount} -> {subject_payment.amount}, "
                    f"status: {subscription.status}, next_payment: {subscription.next_payment_date})"
                )
                return True
            else:
                logger.error(
                    f"CRITICAL: Subscription {subscription.id} update failed verification - "
                    f"status={subscription.status}, amount={subscription.amount}"
                )
                return False

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

                # ✅ Verify subscription creation saved
                subscription.refresh_from_db()
                if subscription.status == SubjectSubscription.Status.ACTIVE:
                    logger.info(
                        f"✅ VERIFIED: Created subscription {subscription.id} for enrollment {enrollment.id} "
                        f"after successful payment (status: {subscription.status}, next_payment: {subscription.next_payment_date})"
                    )
                    return True
                else:
                    logger.error(
                        f"CRITICAL: Subscription {subscription.id} creation failed verification - "
                        f"status={subscription.status} instead of ACTIVE"
                    )
                    return False
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
