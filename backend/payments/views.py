import requests
import json
import uuid
import logging
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import Payment
from .telegram_service import TelegramNotificationService
from core.transaction_utils import (
    TransactionType, 
    transaction_manager, 
    log_critical_operation,
    DataIntegrityValidator
)
from core.json_utils import safe_json_parse, safe_json_response, safe_json_dumps
from django.contrib.auth import get_user_model
from notifications.notification_service import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)

SUCCESS_URL = "/payments/success/"
FAIL_URL = "/payments/fail/"

def _get_safe_url(request, path):
    """Безопасно получает абсолютный URL, обрабатывая случаи без правильного хоста"""
    try:
        if hasattr(request, 'build_absolute_uri'):
            return request.build_absolute_uri(path)
    except Exception:
        pass
    # Fallback для тестовых случаев
    return f"http://localhost:8000{path}"

# Старая функция pay_page удалена - оплата теперь происходит через API

def create_yookassa_payment(payment, request):
    """Создание платежа в ЮКассе с улучшенной валидацией"""
    # Проверяем наличие необходимых настроек
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        logger.error("YOOKASSA_SHOP_ID or YOOKASSA_SECRET_KEY not configured. Please set these environment variables.")
        return None
    
    url = "https://api.yookassa.ru/v3/payments"
    
    # Валидация суммы
    if payment.amount <= 0:
        logger.error(f"Invalid payment amount: {payment.amount}")
        return None
    
    # Получаем URL фронтенда для возврата после оплаты
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
    return_url = f"{frontend_url}/dashboard/parent/payment-success?payment_id={payment.id}"
    
    # Подготовка данных для ЮКассы согласно официальной документации
    # https://yookassa.ru/developers/api#create_payment
    payment_data = {
        "amount": {
            "value": f"{payment.amount:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url
        },
        "capture": True,  # Автоматическое подтверждение платежа
        "description": payment.description or "Оплата услуги",
        "metadata": {
            "payment_id": str(payment.id),
            "service_name": payment.service_name,
            "customer_fio": payment.customer_fio,
        }
    }
    
    headers = {
        'Idempotence-Key': str(uuid.uuid4()),
        'Content-Type': 'application/json'
    }
    
    # Аутентификация через Basic Auth
    auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)
    
    try:
        logger.info(f"Creating YooKassa payment for payment {payment.id}, amount: {payment.amount}")
        logger.debug(f"Payment data: {safe_json_dumps(payment_data)}")
        
        response = requests.post(
            url, 
            headers=headers, 
            data=safe_json_dumps(payment_data), 
            auth=auth,
            timeout=30
        )
        
        logger.info(f"YooKassa API response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = safe_json_response(response)
            if data:
                logger.info(f"YooKassa payment created successfully: {data.get('id')}")
                logger.debug(f"YooKassa response: {safe_json_dumps(data)}")
                return data
            else:
                logger.error(f"Failed to parse YooKassa response. Response text: {response.text[:500]}")
                return None
        else:
            error_text = response.text[:1000] if response.text else "No error message"
            logger.error(f"YooKassa API error: {response.status_code} - {error_text}")
            # Пытаемся распарсить ошибку из ответа
            error_description = None
            try:
                error_data = response.json() if hasattr(response, 'json') else safe_json_response(response)
                if error_data and isinstance(error_data, dict):
                    error_description = error_data.get('description') or error_data.get('message') or error_data.get('type')
                    if error_description:
                        logger.error(f"YooKassa error description: {error_description}")
            except Exception as parse_error:
                logger.debug(f"Could not parse error response: {parse_error}")
            
            # Возвращаем None, чтобы вызывающий код мог обработать ошибку
            # Но логируем детальную информацию
            logger.error(f"YooKassa API error details - Status: {response.status_code}, Description: {error_description}, Text: {error_text[:200]}")
            return None
            
    except requests.exceptions.Timeout as e:
        logger.error(f"YooKassa API timeout: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"YooKassa API connection error: {e}")
        return None
    except requests.RequestException as e:
        logger.error(f"Request error creating YooKassa payment: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating YooKassa payment: {e}", exc_info=True)
        return None

def check_yookassa_payment_status(yookassa_payment_id):
    """Проверяет статус платежа в ЮКассе"""
    url = f"https://api.yookassa.ru/v3/payments/{yookassa_payment_id}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    # Аутентификация через Basic Auth
    auth = (settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)
    
    try:
        response = requests.get(url, headers=headers, auth=auth, timeout=30)
        
        if response.status_code == 200:
            data = safe_json_response(response)
            if data:
                return data.get('status')
            else:
                logger.error("Failed to parse YooKassa status response")
                return None
        else:
            logger.error(f"YooKassa API error: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Request error checking payment status: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error checking payment status: {e}", exc_info=True)
        return None

# Старые функции pay_success и pay_fail удалены - обработка успешной оплаты теперь на фронтенде

@csrf_exempt
def yookassa_webhook(request):
    """Webhook от ЮКассы для обработки уведомлений о статусе платежа"""
    if request.method != "POST":
        logger.warning("Webhook called with non-POST method")
        return HttpResponseBadRequest("POST only")

    try:
        # Получаем данные из webhook
        data = safe_json_parse(request.body)
        if not data:
            logger.error("Invalid JSON in webhook request")
            return HttpResponseBadRequest("Invalid JSON")
        
        logger.info(f"Webhook received: {data.get('type')}")
        
        # Проверяем тип события
        event_type = data.get('type')
        if event_type not in ['payment.succeeded', 'payment.canceled', 'payment.waiting_for_capture']:
            logger.info(f"Ignoring webhook event type: {event_type}")
            return HttpResponse("OK")
        
        # Получаем объект платежа
        payment_object = data.get('object', {})
        yookassa_payment_id = payment_object.get('id')
        
        if not yookassa_payment_id:
            logger.error("Webhook received without payment ID")
            return HttpResponseBadRequest("No payment ID")
        
        # Находим наш платеж
        try:
            payment = Payment.objects.get(yookassa_payment_id=yookassa_payment_id)
            logger.info(f"Found payment: {payment.id}")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for YooKassa ID: {yookassa_payment_id}")
            return HttpResponseBadRequest("Payment not found")
        
        # Сохраняем сырой ответ
        payment.raw_response = data
        
        # Обновляем статус
        if event_type == 'payment.succeeded':
            payment.status = Payment.Status.SUCCEEDED
            payment.paid_at = timezone.now()
            payment.save(update_fields=['status', 'paid_at', 'updated'])
            logger.info(f"Payment {payment.id} marked as succeeded")
            # Дополнительно отмечаем платеж по предмету (если связан)
            try:
                from materials.models import SubjectPayment as SP, SubjectSubscription, SubjectEnrollment
                from notifications.notification_service import NotificationService
                subject_payments = SP.objects.filter(payment=payment)
                for subject_payment in subject_payments:
                    if subject_payment.status != SP.Status.PAID:
                        subject_payment.status = SP.Status.PAID
                        subject_payment.paid_at = payment.paid_at
                        subject_payment.save(update_fields=['status', 'paid_at', 'updated_at'])
                        logger.info(f"SubjectPayment {subject_payment.id} marked as PAID")
                    
                    # Проверяем, нужно ли создать подписку после успешной оплаты
                    create_subscription = payment.metadata.get('create_subscription', False)
                    if create_subscription:
                        try:
                            enrollment = subject_payment.enrollment
                            # Проверяем, существует ли уже подписка для этого enrollment
                            try:
                                subscription = SubjectSubscription.objects.get(enrollment=enrollment)
                                # Если подписка существует, обновляем её
                                old_amount = subscription.amount
                                subscription.amount = subject_payment.amount
                                subscription.status = SubjectSubscription.Status.ACTIVE
                                subscription.next_payment_date = timezone.now() + timedelta(weeks=1)
                                subscription.payment_interval_weeks = 1
                                subscription.cancelled_at = None  # Сбрасываем дату отмены, если была
                                subscription.save()
                                logger.info(f"Updated existing subscription {subscription.id} for enrollment {enrollment.id} (amount: {old_amount} -> {subject_payment.amount})")
                            except SubjectSubscription.DoesNotExist:
                                # Если подписки нет, создаём новую
                                subscription = SubjectSubscription.objects.create(
                                    enrollment=enrollment,
                                    amount=subject_payment.amount,
                                    status=SubjectSubscription.Status.ACTIVE,
                                    next_payment_date=timezone.now() + timedelta(weeks=1),
                                    payment_interval_weeks=1
                                )
                                logger.info(f"Created new subscription {subscription.id} for enrollment {enrollment.id} after successful payment")
                        except Exception as e:
                            logger.error(f"Failed to create/update subscription after payment {payment.id}: {e}", exc_info=True)
                    
                    # Уведомляем родителя, если можно определить
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
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Failed to mark SubjectPayment as PAID for payment {payment.id}: {e}")
            
            # Отправляем уведомление в Telegram
            try:
                telegram_service = TelegramNotificationService()
                telegram_service.send_payment_notification(payment)
                logger.info("Telegram notification sent for payment")
            except Exception as e:
                logger.error(f"Error sending Telegram notification: {e}")
                
        elif event_type == 'payment.canceled':
            payment.status = Payment.Status.CANCELED
            payment.save(update_fields=['status', 'updated'])
            logger.info(f"Payment {payment.id} marked as canceled")
            # Обновляем статус SubjectPayment обратно на PENDING при отмене
            try:
                from materials.models import SubjectPayment as SP
                subject_payments = SP.objects.filter(payment=payment)
                for subject_payment in subject_payments:
                    if subject_payment.status in [SP.Status.WAITING_FOR_PAYMENT]:
                        subject_payment.status = SP.Status.PENDING
                        subject_payment.save(update_fields=['status', 'updated_at'])
                        logger.info(f"SubjectPayment {subject_payment.id} status changed to PENDING after payment cancellation")
            except Exception as e:
                logger.error(f"Failed to update SubjectPayment status after cancellation: {e}")
            
        elif event_type == 'payment.waiting_for_capture':
            payment.status = Payment.Status.WAITING_FOR_CAPTURE
            payment.save(update_fields=['status', 'updated'])
            logger.info(f"Payment {payment.id} marked as waiting for capture")
            # Устанавливаем статус WAITING_FOR_PAYMENT для SubjectPayment
            try:
                from materials.models import SubjectPayment as SP
                subject_payments = SP.objects.filter(payment=payment)
                for subject_payment in subject_payments:
                    if subject_payment.status == SP.Status.PENDING:
                        subject_payment.status = SP.Status.WAITING_FOR_PAYMENT
                        subject_payment.save(update_fields=['status', 'updated_at'])
                        logger.info(f"SubjectPayment {subject_payment.id} status changed to WAITING_FOR_PAYMENT")
            except Exception as e:
                logger.error(f"Failed to update SubjectPayment status to WAITING_FOR_PAYMENT: {e}")
        
        return HttpResponse("OK")
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return HttpResponseBadRequest("Error processing webhook")

@csrf_exempt
def check_payment_status(request):
    """API endpoint для проверки статуса платежа"""
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)
    
    payment_id = request.GET.get('payment_id')
    if not payment_id:
        return JsonResponse({"error": "payment_id required"}, status=400)
    
    try:
        payment = Payment.objects.get(id=payment_id)
        
        # Проверяем статус в ЮКассе если есть ID
        if payment.yookassa_payment_id:
            yookassa_status = check_yookassa_payment_status(payment.yookassa_payment_id)
            if yookassa_status:
                # Обновляем статус если нужно
                if yookassa_status == 'succeeded' and payment.status != Payment.Status.SUCCEEDED:
                    payment.status = Payment.Status.SUCCEEDED
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=['status', 'paid_at', 'updated'])
                    # Синхронизация статуса предметного платежа
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status != SubjectPaymentModel.Status.PAID:
                                sp.status = SubjectPaymentModel.Status.PAID
                                sp.paid_at = payment.paid_at
                                sp.save(update_fields=['status', 'paid_at', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} marked as PAID")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment for payment {payment.id}: {sync_err}", exc_info=True)
                    
                    # Отправляем уведомление в Telegram
                    try:
                        telegram_service = TelegramNotificationService()
                        telegram_service.send_payment_notification(payment)
                    except Exception as e:
                        logger.error(f"Error sending Telegram notification: {e}", exc_info=True)
                elif yookassa_status == 'canceled' and payment.status != Payment.Status.CANCELED:
                    payment.status = Payment.Status.CANCELED
                    payment.save(update_fields=['status', 'updated'])
                    # Обновляем статус SubjectPayment обратно на PENDING при отмене
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status in [SubjectPaymentModel.Status.WAITING_FOR_PAYMENT]:
                                sp.status = SubjectPaymentModel.Status.PENDING
                                sp.save(update_fields=['status', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} status changed to PENDING after payment cancellation")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment status after cancellation for payment {payment.id}: {sync_err}", exc_info=True)
                elif yookassa_status == 'waiting_for_capture' and payment.status != Payment.Status.WAITING_FOR_CAPTURE:
                    payment.status = Payment.Status.WAITING_FOR_CAPTURE
                    payment.save(update_fields=['status', 'updated'])
                    # Устанавливаем статус WAITING_FOR_PAYMENT для SubjectPayment
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status in [SubjectPaymentModel.Status.PENDING]:
                                sp.status = SubjectPaymentModel.Status.WAITING_FOR_PAYMENT
                                sp.save(update_fields=['status', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} status changed to WAITING_FOR_PAYMENT")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment status to WAITING_FOR_PAYMENT for payment {payment.id}: {sync_err}", exc_info=True)
                elif yookassa_status == 'pending' and payment.confirmation_url:
                    # Если платеж в статусе pending и есть confirmation_url, это тоже ожидание оплаты
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status == SubjectPaymentModel.Status.PENDING:
                                sp.status = SubjectPaymentModel.Status.WAITING_FOR_PAYMENT
                                sp.save(update_fields=['status', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} status changed to WAITING_FOR_PAYMENT (pending with confirmation_url)")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment status to WAITING_FOR_PAYMENT for payment {payment.id}: {sync_err}", exc_info=True)
        
        return JsonResponse({
            "status": payment.status,
            "amount": str(payment.amount),
            "description": payment.description,
            "service_name": payment.service_name,
            "customer_fio": payment.customer_fio,
            "created": payment.created.isoformat(),
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
        })
        
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)
    except Exception as e:
        logger.error(f"Error checking payment status: {e}", exc_info=True)
        return JsonResponse({"error": "Internal server error"}, status=500)


# API Views
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import PaymentSerializer, PaymentCreateSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления платежами через API
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def create(self, request, *args, **kwargs):
        """Создание нового платежа"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Создаем платеж
        payment = serializer.save()
        
        # Создаем платеж в ЮКассе
        yookassa_payment = create_yookassa_payment(payment, request)
        
        if yookassa_payment:
            # Обновляем платеж с данными от ЮКассы
            payment.yookassa_payment_id = yookassa_payment.get('id')
            payment.confirmation_url = yookassa_payment.get('confirmation', {}).get('confirmation_url')
            payment.return_url = f"{request.build_absolute_uri(SUCCESS_URL)}?payment_id={payment.id}"
            payment.raw_response = yookassa_payment
            
            # Обновляем статус Payment на основе ответа от ЮКассы
            yookassa_status = yookassa_payment.get('status')
            update_fields = ['yookassa_payment_id', 'confirmation_url', 'return_url', 'raw_response', 'status', 'updated']
            
            if yookassa_status == 'pending':
                payment.status = Payment.Status.PENDING
            elif yookassa_status == 'waiting_for_capture':
                payment.status = Payment.Status.WAITING_FOR_CAPTURE
            elif yookassa_status == 'succeeded':
                payment.status = Payment.Status.SUCCEEDED
                payment.paid_at = timezone.now()
                update_fields.append('paid_at')
            elif yookassa_status == 'canceled':
                payment.status = Payment.Status.CANCELED
            
            payment.save(update_fields=update_fields)
            
            # Обрабатываем связь с SubjectPayment, если есть в metadata
            # Это важно для случаев, когда платеж создается через PaymentViewSet.create
            metadata = payment.metadata or {}
            subject_payment_id = metadata.get('subject_payment_id')
            enrollment_id = metadata.get('enrollment_id')
            
            if subject_payment_id or enrollment_id:
                try:
                    from materials.models import SubjectPayment as SP, SubjectEnrollment
                    from datetime import timedelta
                    
                    # Определяем статус для SubjectPayment на основе статуса Payment и наличия confirmation_url
                    # Если есть confirmation_url, значит платеж ожидает оплаты
                    payment_status = SP.Status.WAITING_FOR_PAYMENT if payment.confirmation_url else SP.Status.PENDING
                    
                    # Если указан subject_payment_id, обновляем существующий
                    if subject_payment_id:
                        try:
                            subject_payment = SP.objects.get(id=subject_payment_id)
                            # Формируем список полей для обновления
                            update_fields_list = ['updated_at']
                            
                            # Обновляем связь с Payment, если еще не установлена
                            if not subject_payment.payment_id:
                                subject_payment.payment = payment
                                update_fields_list.append('payment')
                            
                            # Устанавливаем статус на основе наличия confirmation_url
                            if payment.confirmation_url and subject_payment.status == SP.Status.PENDING:
                                subject_payment.status = payment_status
                                update_fields_list.append('status')
                            elif not payment.confirmation_url and subject_payment.status != payment_status:
                                subject_payment.status = payment_status
                                update_fields_list.append('status')
                            
                            subject_payment.save(update_fields=update_fields_list)
                            logger.info(f"Updated SubjectPayment {subject_payment.id} with Payment {payment.id}, status: {subject_payment.status}")
                        except SP.DoesNotExist:
                            logger.warning(f"SubjectPayment with id {subject_payment_id} not found")
                            # Если SubjectPayment не найден, но есть enrollment_id, создаем новый
                            if enrollment_id:
                                try:
                                    enrollment = SubjectEnrollment.objects.get(id=enrollment_id)
                                    due_date = timezone.now() + timedelta(days=7)
                                    subject_payment = SP.objects.create(
                                        enrollment=enrollment,
                                        payment=payment,
                                        amount=payment.amount,
                                        status=payment_status,
                                        due_date=due_date
                                    )
                                    logger.info(f"Created new SubjectPayment {subject_payment.id} for enrollment {enrollment_id}")
                                except SubjectEnrollment.DoesNotExist:
                                    logger.error(f"Enrollment with id {enrollment_id} not found")
                    
                    # Если указан только enrollment_id (без subject_payment_id), создаем новый SubjectPayment
                    elif enrollment_id and not subject_payment_id:
                        try:
                            enrollment = SubjectEnrollment.objects.get(id=enrollment_id)
                            due_date = timezone.now() + timedelta(days=7)
                            subject_payment = SP.objects.create(
                                enrollment=enrollment,
                                payment=payment,
                                amount=payment.amount,
                                status=payment_status,
                                due_date=due_date
                            )
                            logger.info(f"Created new SubjectPayment {subject_payment.id} for enrollment {enrollment_id}")
                        except SubjectEnrollment.DoesNotExist:
                            logger.error(f"Enrollment with id {enrollment_id} not found")
                
                except Exception as e:
                    logger.error(f"Failed to link Payment {payment.id} with SubjectPayment: {e}", exc_info=True)
                    # Не прерываем создание платежа из-за ошибки связи с SubjectPayment
            
            # Возвращаем данные платежа
            response_serializer = PaymentSerializer(payment)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            # Если платеж не создан в ЮКассе, удаляем его
            payment.delete()
            return Response(
                {"error": "Ошибка создания платежа в ЮКассе"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Получение статуса платежа"""
        payment = self.get_object()
        
        # Проверяем статус в ЮКассе если есть ID
        if payment.yookassa_payment_id:
            yookassa_status = check_yookassa_payment_status(payment.yookassa_payment_id)
            if yookassa_status:
                # Обновляем статус если нужно
                if yookassa_status == 'succeeded' and payment.status != Payment.Status.SUCCEEDED:
                    payment.status = Payment.Status.SUCCEEDED
                    payment.paid_at = timezone.now()
                    payment.save(update_fields=['status', 'paid_at', 'updated'])
                    # Синхронизация статуса предметного платежа
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status != SubjectPaymentModel.Status.PAID:
                                sp.status = SubjectPaymentModel.Status.PAID
                                sp.paid_at = payment.paid_at
                                sp.save(update_fields=['status', 'paid_at', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} marked as PAID")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment for payment {payment.id}: {sync_err}", exc_info=True)
                elif yookassa_status == 'canceled' and payment.status != Payment.Status.CANCELED:
                    payment.status = Payment.Status.CANCELED
                    payment.save(update_fields=['status', 'updated'])
                    # Обновляем статус SubjectPayment обратно на PENDING при отмене
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status in [SubjectPaymentModel.Status.WAITING_FOR_PAYMENT]:
                                sp.status = SubjectPaymentModel.Status.PENDING
                                sp.save(update_fields=['status', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} status changed to PENDING after payment cancellation")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment status after cancellation for payment {payment.id}: {sync_err}", exc_info=True)
                elif yookassa_status == 'waiting_for_capture' and payment.status != Payment.Status.WAITING_FOR_CAPTURE:
                    payment.status = Payment.Status.WAITING_FOR_CAPTURE
                    payment.save(update_fields=['status', 'updated'])
                    # Устанавливаем статус WAITING_FOR_PAYMENT для SubjectPayment
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status in [SubjectPaymentModel.Status.PENDING]:
                                sp.status = SubjectPaymentModel.Status.WAITING_FOR_PAYMENT
                                sp.save(update_fields=['status', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} status changed to WAITING_FOR_PAYMENT")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment status to WAITING_FOR_PAYMENT for payment {payment.id}: {sync_err}", exc_info=True)
                elif yookassa_status == 'pending' and payment.confirmation_url:
                    # Если платеж в статусе pending и есть confirmation_url, это тоже ожидание оплаты
                    try:
                        from materials.models import SubjectPayment as SubjectPaymentModel
                        subject_payments = SubjectPaymentModel.objects.filter(payment=payment)
                        for sp in subject_payments:
                            if sp.status == SubjectPaymentModel.Status.PENDING:
                                sp.status = SubjectPaymentModel.Status.WAITING_FOR_PAYMENT
                                sp.save(update_fields=['status', 'updated_at'])
                                logger.info(f"SubjectPayment {sp.id} status changed to WAITING_FOR_PAYMENT (pending with confirmation_url)")
                    except Exception as sync_err:
                        logger.error(f"Failed to sync SubjectPayment status to WAITING_FOR_PAYMENT for payment {payment.id}: {sync_err}", exc_info=True)
        
        serializer = PaymentSerializer(payment)
        return Response(serializer.data)