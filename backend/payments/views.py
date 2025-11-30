import requests
import json
import uuid
import logging
from decimal import Decimal
from datetime import timedelta
from ipaddress import ip_address, ip_network
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
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
from core.environment import EnvConfig
from django.contrib.auth import get_user_model
from notifications.notification_service import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)
env_config = EnvConfig()

SUCCESS_URL = "/payments/success/"
FAIL_URL = "/payments/fail/"

# Официальные IP-адреса YooKassa для webhooks
# Источник: https://yookassa.ru/developers/using-api/webhooks#ip
YOOKASSA_WEBHOOK_IPS = [
    '185.71.76.0/27',
    '185.71.77.0/27',
    '77.75.153.0/25',
    '77.75.156.11',
    '77.75.156.35',
    '77.75.154.128/25',
    '2a02:5180::/32',
]


def verify_yookassa_ip(request):
    """
    Проверяет, что запрос пришел с IP-адреса YooKassa.

    Args:
        request: Django request object

    Returns:
        bool: True если IP разрешен, False если нет
    """
    # Получаем IP-адрес клиента
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Берем первый IP из списка (клиентский IP)
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR')

    if not client_ip:
        logger.warning("Could not determine client IP address")
        return False

    try:
        client_ip_obj = ip_address(client_ip)

        # Проверяем, входит ли IP в разрешенные сети
        for allowed_network in YOOKASSA_WEBHOOK_IPS:
            try:
                if '/' in allowed_network:
                    # Это сеть
                    if client_ip_obj in ip_network(allowed_network, strict=False):
                        logger.info(f"YooKassa webhook IP {client_ip} verified (network: {allowed_network})")
                        return True
                else:
                    # Это конкретный IP
                    if str(client_ip_obj) == allowed_network:
                        logger.info(f"YooKassa webhook IP {client_ip} verified")
                        return True
            except ValueError as e:
                logger.error(f"Invalid network in YOOKASSA_WEBHOOK_IPS: {allowed_network}: {e}")
                continue

        logger.warning(f"YooKassa webhook from unverified IP: {client_ip}")
        return False

    except ValueError as e:
        logger.error(f"Invalid client IP address: {client_ip}: {e}")
        return False

def _get_safe_url(request, path):
    """Безопасно получает абсолютный URL, обрабатывая случаи без правильного хоста"""
    try:
        if hasattr(request, 'build_absolute_uri'):
            return request.build_absolute_uri(path)
    except Exception:
        pass
    # Fallback для тестовых случаев - используем FRONTEND_URL из settings
    from django.conf import settings
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
    return f"{frontend_url.rstrip('/')}{path}"

# Старая функция pay_page удалена - оплата теперь происходит через API

def create_yookassa_payment(payment, request):
    """
    Создание платежа в ЮКассе с улучшенной валидацией и обработкой ошибок.

    Args:
        payment: Payment объект из БД
        request: Django request object для построения URL

    Returns:
        dict: YooKassa payment data если успешно
        dict: {'error': str, 'error_type': str} если ошибка (для информативной обработки)
        None: если критическая ошибка (устаревший формат для обратной совместимости)
    """
    # Проверяем наличие необходимых настроек
    if not settings.YOOKASSA_SHOP_ID or not settings.YOOKASSA_SECRET_KEY:
        logger.error("YOOKASSA_SHOP_ID or YOOKASSA_SECRET_KEY not configured. Please set these environment variables.")
        return {
            'error': 'Ошибка конфигурации платежной системы. Обратитесь к администратору.',
            'error_type': 'configuration_error',
            'technical_details': 'YOOKASSA credentials not configured'
        }

    # Use environment-aware YooKassa API URL
    url = f"{env_config.get_yookassa_api_url()}/payments"
    
    # Валидация суммы
    if payment.amount <= 0:
        logger.error(f"Invalid payment amount: {payment.amount}")
        return {
            'error': 'Неверная сумма платежа',
            'error_type': 'invalid_amount',
            'technical_details': f'Amount must be > 0, got {payment.amount}'
        }
    
    # Получаем URL фронтенда для возврата после оплаты
    # Используем FRONTEND_URL из настроек (должен быть установлен в .env для продакшена)
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
    
    # Если FRONTEND_URL все еще localhost, но есть request с реальным доменом,
    # пытаемся определить правильный URL на основе request
    if 'localhost' in frontend_url and request and hasattr(request, 'get_host'):
        try:
            host = request.get_host()
            # Если это реальный домен (не localhost), используем его для определения протокола
            if host and 'localhost' not in host and '127.0.0.1' not in host:
                # Определяем протокол (http или https)
                protocol = 'https' if request.is_secure() else 'http'
                # Используем тот же домен, но убеждаемся, что используем правильный протокол
                # Если FRONTEND_URL в настройках содержит правильный домен, используем его
                # Иначе формируем на основе request
                if env_config.PRODUCTION_DOMAIN in host or f'www.{env_config.PRODUCTION_DOMAIN}' in host:
                    frontend_url = f"{protocol}://{host.split(':')[0]}"  # Убираем порт если есть
                    logger.warning(f"FRONTEND_URL was localhost, but detected production domain. Using {frontend_url}. "
                                 f"Please set FRONTEND_URL in .env file for production!")
                    # Если frontend на другом порту, нужно указать его в FRONTEND_URL в .env
        except Exception as e:
            logger.debug(f"Could not determine host from request: {e}, using FRONTEND_URL from settings: {frontend_url}")
    
    # Проверяем, что на продакшене не используется localhost
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
    has_production_host = any(env_config.PRODUCTION_DOMAIN in str(h) for h in allowed_hosts) if allowed_hosts else False
    if has_production_host and 'localhost' in frontend_url:
        logger.warning(f"WARNING: Production server detected, but FRONTEND_URL is set to localhost: {frontend_url}. "
                      f"Please set FRONTEND_URL in .env file to your production frontend URL (e.g., https://{env_config.PRODUCTION_DOMAIN})")
    
    # Убеждаемся, что URL не заканчивается на слэш
    frontend_url = frontend_url.rstrip('/')
    return_url = f"{frontend_url}/dashboard/parent/payment-success?payment_id={payment.id}"
    
    logger.info(f"Using frontend URL for return: {frontend_url}, return_url: {return_url}")
    
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
            # Передаем ВСЕ метаданные из payment.metadata без фильтрации
            # Критично: subject_payment_id нужен для связи Payment ↔ SubjectPayment
            **(payment.metadata or {})
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
            error_code = None
            user_message = "Ошибка создания платежа в платежной системе"

            try:
                error_data = response.json() if hasattr(response, 'json') else safe_json_response(response)
                if error_data and isinstance(error_data, dict):
                    error_description = error_data.get('description') or error_data.get('message') or error_data.get('type')
                    error_code = error_data.get('code')
                    if error_description:
                        logger.error(f"YooKassa error description: {error_description}")

                    # Определяем понятное для пользователя сообщение на основе типа ошибки
                    if response.status_code == 401 or response.status_code == 403:
                        user_message = "Ошибка конфигурации платежной системы. Обратитесь к администратору."
                    elif 'amount' in str(error_description).lower():
                        user_message = "Неверная сумма платежа"
                    elif 'invalid' in str(error_description).lower() and 'credentials' in str(error_description).lower():
                        user_message = "Ошибка конфигурации платежной системы. Обратитесь к администратору."
            except Exception as parse_error:
                logger.debug(f"Could not parse error response: {parse_error}")

            # Логируем детальную информацию
            logger.error(
                f"YooKassa API error details - Status: {response.status_code}, "
                f"Code: {error_code}, Description: {error_description}, Text: {error_text[:200]}"
            )

            return {
                'error': user_message,
                'error_type': 'yookassa_api_error',
                'technical_details': f'Status: {response.status_code}, Description: {error_description}',
                'status_code': response.status_code,
                'error_code': error_code
            }
            
    except requests.exceptions.Timeout as e:
        logger.error(f"YooKassa API timeout: {e}")
        return {
            'error': 'Не удалось связаться с платежной системой. Попробуйте позже.',
            'error_type': 'network_timeout',
            'technical_details': str(e)
        }
    except requests.exceptions.ConnectionError as e:
        logger.error(f"YooKassa API connection error: {e}")
        return {
            'error': 'Не удалось связаться с платежной системой. Попробуйте позже.',
            'error_type': 'network_connection_error',
            'technical_details': str(e)
        }
    except requests.RequestException as e:
        logger.error(f"Request error creating YooKassa payment: {e}", exc_info=True)
        return {
            'error': 'Ошибка при обращении к платежной системе. Попробуйте позже.',
            'error_type': 'network_request_error',
            'technical_details': str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error creating YooKassa payment: {e}", exc_info=True)
        return {
            'error': 'Произошла неожиданная ошибка. Попробуйте позже или обратитесь к администратору.',
            'error_type': 'unexpected_error',
            'technical_details': str(e)
        }

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

    # Проверяем IP-адрес отправителя для безопасности
    if not verify_yookassa_ip(request):
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
        logger.error(f"Webhook request from unauthorized IP: {client_ip}")
        return HttpResponseForbidden("Unauthorized IP address")

    try:
        # Получаем данные из webhook
        data = safe_json_parse(request.body)
        if not data:
            logger.error("Invalid JSON in webhook request")
            return HttpResponseBadRequest("Invalid JSON")

        logger.info(f"Webhook received: {data.get('type')}")

        # Проверяем тип события
        event_type = data.get('type')
        supported_events = [
            'payment.succeeded',
            'payment.canceled',
            'payment.waiting_for_capture',
            'payment.failed',
            'refund.succeeded'
        ]
        if event_type not in supported_events:
            logger.info(f"Ignoring webhook event type: {event_type}")
            return HttpResponse("OK")

        # Получаем объект платежа
        payment_object = data.get('object', {})
        yookassa_payment_id = payment_object.get('id')

        if not yookassa_payment_id:
            logger.error("Webhook received without payment ID")
            return HttpResponseBadRequest("No payment ID")

        # Оборачиваем всю обработку в транзакцию для обеспечения атомичности
        from django.db import transaction as db_transaction

        with db_transaction.atomic():
            # Используем select_for_update() для блокировки платежа при обработке webhook
            # Это обеспечивает атомичность и предотвращает race condition с дублирующимися webhook'ами
            try:
                payment = Payment.objects.select_for_update().get(yookassa_payment_id=yookassa_payment_id)
                logger.info(f"Found payment: {payment.id}")
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for YooKassa ID: {yookassa_payment_id}")
                return HttpResponseBadRequest("Payment not found")

            # Сохраняем сырой ответ
            payment.raw_response = data

            # Обновляем статус
            if event_type == 'payment.succeeded':
                # Idempotency: проверяем, не был ли платеж уже обработан (внутри транзакции с блокировкой)
                if payment.status == Payment.Status.SUCCEEDED:
                    logger.info(f"Payment {payment.id} already processed as SUCCEEDED, skipping")
                    return HttpResponse('OK')

                # Используем централизованную функцию для обработки успешного платежа
                from payments.services import process_successful_payment

                result = process_successful_payment(payment)

                if result['success']:
                    logger.info(
                        f"Webhook payment.succeeded processed successfully: "
                        f"payment_id={payment.id}, "
                        f"subject_payments_updated={result['subject_payments_updated']}, "
                        f"enrollments_activated={result['enrollments_activated']}, "
                        f"subscriptions_processed={result['subscriptions_processed']}"
                    )
                else:
                    logger.error(
                        f"Webhook payment.succeeded processing had errors: "
                        f"payment_id={payment.id}, "
                        f"errors={result['errors']}"
                    )

                # CRITICAL FIX: Invalidate YooKassa status cache after webhook processing
                # This prevents check_payment_status() from serving stale cached data
                # If webhook processed payment as SUCCEEDED, cache should not return "pending"
                from django.core.cache import cache
                cache_key = f"yookassa_status_{payment.yookassa_payment_id}"
                cache.delete(cache_key)
                logger.info(f"Invalidated YooKassa status cache for payment {payment.yookassa_payment_id}")

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

                # CRITICAL FIX: Invalidate cache for canceled payments too
                from django.core.cache import cache
                cache_key = f"yookassa_status_{payment.yookassa_payment_id}"
                cache.delete(cache_key)
                logger.info(f"Invalidated YooKassa status cache for canceled payment {payment.yookassa_payment_id}")

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

            elif event_type == 'payment.failed':
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=['status', 'updated'])
                logger.info(f"Payment {payment.id} marked as failed")

                # CRITICAL FIX: Invalidate cache for failed payments too
                from django.core.cache import cache
                cache_key = f"yookassa_status_{payment.yookassa_payment_id}"
                cache.delete(cache_key)
                logger.info(f"Invalidated YooKassa status cache for failed payment {payment.yookassa_payment_id}")

                # Обновляем статус SubjectPayment обратно на PENDING при ошибке
                try:
                    from materials.models import SubjectPayment as SP
                    subject_payments = SP.objects.filter(payment=payment)
                    for subject_payment in subject_payments:
                        if subject_payment.status in [SP.Status.WAITING_FOR_PAYMENT]:
                            subject_payment.status = SP.Status.PENDING
                            subject_payment.save(update_fields=['status', 'updated_at'])
                            logger.info(f"SubjectPayment {subject_payment.id} status changed to PENDING after payment failure")
                except Exception as e:
                    logger.error(f"Failed to update SubjectPayment status after payment failure: {e}")

            elif event_type == 'refund.succeeded':
                # Для refund объект содержит payment_id оригинального платежа
                refund_object = data.get('object', {})
                payment_id_from_refund = refund_object.get('payment_id')

                if not payment_id_from_refund:
                    logger.error("Refund webhook received without payment_id")
                    return HttpResponseBadRequest("No payment_id in refund")

                # Находим оригинальный платеж
                try:
                    original_payment = Payment.objects.get(yookassa_payment_id=payment_id_from_refund)
                    original_payment.status = Payment.Status.REFUNDED
                    original_payment.raw_response = data  # Сохраняем данные о возврате
                    original_payment.save(update_fields=['status', 'raw_response', 'updated'])
                    logger.info(f"Payment {original_payment.id} marked as REFUNDED")

                    # CRITICAL FIX: Invalidate cache for refunded payments too
                    from django.core.cache import cache
                    cache_key = f"yookassa_status_{original_payment.yookassa_payment_id}"
                    cache.delete(cache_key)
                    logger.info(f"Invalidated YooKassa status cache for refunded payment {original_payment.yookassa_payment_id}")

                    # Обновляем статус SubjectPayment на REFUNDED
                    try:
                        from materials.models import SubjectPayment as SP
                        subject_payments = SP.objects.filter(payment=original_payment)
                        for subject_payment in subject_payments:
                            subject_payment.status = SP.Status.REFUNDED
                            subject_payment.save(update_fields=['status', 'updated_at'])
                            logger.info(f"SubjectPayment {subject_payment.id} marked as REFUNDED")

                            # Уведомляем родителя о возврате
                            try:
                                from notifications.notification_service import NotificationService
                                student = subject_payment.enrollment.student
                                parent = getattr(student.student_profile, 'parent', None) if hasattr(student, 'student_profile') else None
                                if parent:
                                    NotificationService().notify_payment_processed(
                                        parent=parent,
                                        status='refunded',
                                        amount=str(subject_payment.amount),
                                        enrollment_id=subject_payment.enrollment.id,
                                    )
                            except Exception:
                                pass
                    except Exception as e:
                        logger.error(f"Failed to update SubjectPayment status after refund: {e}")

                except Payment.DoesNotExist:
                    logger.error(f"Original payment not found for refund: {payment_id_from_refund}")
                    return HttpResponseBadRequest("Original payment not found")

            return HttpResponse("OK")
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return HttpResponseBadRequest("Error processing webhook")

@csrf_exempt
def check_payment_status(request):
    """
    API endpoint для проверки статуса платежа.

    CRITICAL: DB status is the source of truth after webhook processing.
    Cache is only used for YooKassa API responses to reduce load, but DB status always takes precedence.
    """
    if request.method != "GET":
        return JsonResponse({"error": "GET only"}, status=405)

    payment_id = request.GET.get('payment_id')
    if not payment_id:
        return JsonResponse({"error": "payment_id required"}, status=400)

    try:
        payment = Payment.objects.get(id=payment_id)

        # CRITICAL FIX: Check DB status FIRST - this is the source of truth
        # If webhook already processed payment as SUCCEEDED, return immediately
        # This prevents race condition where cached YooKassa status is stale
        if payment.status == Payment.Status.SUCCEEDED:
            logger.debug(f"Payment {payment.id} already SUCCEEDED in DB, returning immediately (no YooKassa check needed)")
            return JsonResponse({
                "status": payment.status,
                "amount": str(payment.amount),
                "description": payment.description,
                "service_name": payment.service_name,
                "customer_fio": payment.customer_fio,
                "created": payment.created.isoformat(),
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
            })

        # CRITICAL FIX: Also check for other terminal states in DB
        # If payment is CANCELED, FAILED, or REFUNDED in DB, trust the DB (webhook already processed)
        if payment.status in [Payment.Status.CANCELED, Payment.Status.FAILED, Payment.Status.REFUNDED]:
            logger.debug(f"Payment {payment.id} in terminal state {payment.status} in DB, returning immediately")
            return JsonResponse({
                "status": payment.status,
                "amount": str(payment.amount),
                "description": payment.description,
                "service_name": payment.service_name,
                "customer_fio": payment.customer_fio,
                "created": payment.created.isoformat(),
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
            })

        # Only check YooKassa if DB status is still PENDING or WAITING_FOR_CAPTURE
        # These are the only states where we need to poll YooKassa for updates
        if payment.yookassa_payment_id:
            # OPTIMIZATION: Cache YooKassa API response for 5 seconds to reduce load
            # BUT: Cache is ONLY used for YooKassa API calls, NOT for DB status
            # If webhook arrives and updates DB, next poll will hit DB check above and skip cache
            from django.core.cache import cache
            cache_key = f"yookassa_status_{payment.yookassa_payment_id}"
            yookassa_status = cache.get(cache_key)

            if yookassa_status is None:
                logger.debug(f"Checking YooKassa API for payment {payment.id} (not in cache)")
                yookassa_status = check_yookassa_payment_status(payment.yookassa_payment_id)
                # Cache for 5 seconds to prevent aggressive polling
                if yookassa_status:
                    cache.set(cache_key, yookassa_status, 5)
                    logger.debug(f"Cached YooKassa status '{yookassa_status}' for payment {payment.id}")
            else:
                logger.debug(f"YooKassa status '{yookassa_status}' for payment {payment.id} from cache")

            if yookassa_status:
                # Process YooKassa status and update DB if needed
                if yookassa_status == 'succeeded' and payment.status != Payment.Status.SUCCEEDED:
                    # Используем централизованную функцию для обработки успешного платежа
                    from payments.services import process_successful_payment

                    result = process_successful_payment(payment)

                    if result['success']:
                        logger.info(
                            f"Payment {payment.id} processed via check_payment_status: "
                            f"subject_payments={result['subject_payments_updated']}, "
                            f"enrollments={result['enrollments_activated']}, "
                            f"subscriptions={result['subscriptions_processed']}, "
                            f"notifications={result['notifications_sent']}"
                        )
                    else:
                        logger.error(
                            f"Payment {payment.id} processing via check_payment_status completed with errors: {result['errors']}"
                        )

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

        # Проверяем, является ли ответ ошибкой
        if yookassa_payment and 'error' in yookassa_payment:
            # Это ошибка - логируем и помечаем платеж как неудавшийся
            error_info = yookassa_payment
            logger.error(
                f"YooKassa payment creation failed for payment {payment.id}: "
                f"{error_info.get('error_type', 'unknown')} - {error_info.get('technical_details', 'N/A')}"
            )

            # Не удаляем платеж, а помечаем как неудавшийся для аудита
            payment.status = Payment.Status.CANCELED
            payment.raw_response = {
                'error': error_info.get('error'),
                'error_type': error_info.get('error_type'),
                'technical_details': error_info.get('technical_details'),
                'timestamp': timezone.now().isoformat()
            }
            payment.save(update_fields=['status', 'raw_response', 'updated'])

            # Возвращаем понятное пользователю сообщение об ошибке
            return Response(
                {
                    "error": error_info.get('error', 'Ошибка создания платежа в ЮКассе'),
                    "error_type": error_info.get('error_type'),
                    "payment_id": payment.id
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        elif yookassa_payment:
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
            # Если платеж не создан в ЮКассе (неожиданный случай - должен возвращаться error dict)
            logger.error(f"Unexpected: create_yookassa_payment returned None/empty for payment {payment.id}")

            # Не удаляем платеж, а помечаем как неудавшийся для аудита
            payment.status = Payment.Status.CANCELED
            payment.raw_response = {
                'error': 'Неизвестная ошибка при создании платежа',
                'timestamp': timezone.now().isoformat()
            }
            payment.save(update_fields=['status', 'raw_response', 'updated'])

            return Response(
                {
                    "error": "Ошибка создания платежа в ЮКассе",
                    "payment_id": payment.id
                },
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Получение статуса платежа.

        CRITICAL: DB status is the source of truth after webhook processing.
        Only poll YooKassa if payment is in non-terminal state (PENDING/WAITING_FOR_CAPTURE).
        """
        payment = self.get_object()

        # CRITICAL FIX: Check DB status FIRST - if already in terminal state, return immediately
        # This prevents unnecessary YooKassa API calls and avoids stale cached data
        if payment.status in [Payment.Status.SUCCEEDED, Payment.Status.CANCELED, Payment.Status.FAILED, Payment.Status.REFUNDED]:
            logger.debug(f"PaymentViewSet.status: Payment {payment.id} in terminal state {payment.status}, returning DB status")
            serializer = PaymentSerializer(payment)
            return Response(serializer.data)

        # Only check YooKassa if DB status is still PENDING or WAITING_FOR_CAPTURE
        if payment.yookassa_payment_id:
            yookassa_status = check_yookassa_payment_status(payment.yookassa_payment_id)
            if yookassa_status:
                # Обновляем статус если нужно
                if yookassa_status == 'succeeded' and payment.status != Payment.Status.SUCCEEDED:
                    # Используем централизованную функцию для полной обработки платежа
                    from payments.services import process_successful_payment

                    result = process_successful_payment(payment)

                    if result['success']:
                        logger.info(
                            f"PaymentViewSet.status processed successful payment {payment.id}: "
                            f"subject_payments_updated={result['subject_payments_updated']}, "
                            f"enrollments_activated={result['enrollments_activated']}, "
                            f"subscriptions_processed={result['subscriptions_processed']}"
                        )
                    else:
                        logger.error(
                            f"PaymentViewSet.status had errors processing payment {payment.id}: "
                            f"errors={result['errors']}"
                        )
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