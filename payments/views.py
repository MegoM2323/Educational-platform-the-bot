import requests
import json
import uuid
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import Payment
from .telegram_service import TelegramNotificationService

SUCCESS_URL = "/payments/success/"
FAIL_URL = "/payments/fail/"

def pay_page(request):
    """Страница создания платежа"""
    if request.method == "POST":
        service_name = (request.POST.get("service_name") or "").strip()
        customer_fio = (request.POST.get("customer_fio") or "").strip()
        raw_amount = (request.POST.get("amount") or "0").replace(",", ".")
        
        try:
            amount = Decimal(raw_amount)
        except Exception:
            return HttpResponseBadRequest("Некорректная сумма")
            
        if not service_name or not customer_fio or amount <= 0:
            return HttpResponseBadRequest("Заполните все поля корректно")

        # Создаем платеж в нашей системе
        payment = Payment.objects.create(
            amount=amount,
            service_name=service_name,
            customer_fio=customer_fio,
            description=f"Услуга: {service_name}; Плательщик: {customer_fio}",
            metadata={
                "service_name": service_name,
                "customer_fio": customer_fio,
            }
        )

        # Создаем платеж в ЮКассе
        yookassa_payment = create_yookassa_payment(payment, request)
        
        if yookassa_payment:
            # Сохраняем ID платежа ЮКассы и URL подтверждения
            payment.yookassa_payment_id = yookassa_payment.get('id')
            payment.confirmation_url = yookassa_payment.get('confirmation', {}).get('confirmation_url')
            payment.return_url = f"{request.build_absolute_uri(SUCCESS_URL)}?payment_id={payment.id}"
            payment.raw_response = yookassa_payment
            payment.save()
            
            # Перенаправляем на страницу подтверждения
            return render(request, "payments/redirect_form.html", {
                "payment": payment,
                "confirmation_url": payment.confirmation_url,
                "amount": payment.amount,
                "description": payment.description,
            })
        else:
            return HttpResponseBadRequest("Ошибка создания платежа")
    
    return render(request, "payments/pay.html")

def create_yookassa_payment(payment, request):
    """Создание платежа в ЮКассе"""
    url = "https://api.yookassa.ru/v3/payments"
    
    # Подготовка данных для ЮКассы
    payment_data = {
        "amount": {
            "value": str(payment.amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{request.build_absolute_uri(SUCCESS_URL)}?payment_id={payment.id}"
        },
        "capture": True,
        "description": payment.description,
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
        response = requests.post(
            url, 
            headers=headers, 
            data=json.dumps(payment_data), 
            auth=auth,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"YooKassa API error: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Request error: {e}")
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
            data = response.json()
            return data.get('status')
        else:
            print(f"YooKassa API error: {response.status_code} - {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"Request error checking payment status: {e}")
        return None

def pay_success(request):
    """Страница успешной оплаты"""
    # Получаем ID платежа из параметров
    payment_id = request.GET.get('payment_id')
    
    if not payment_id:
        return render(request, "payments/fail.html", {
            "error": "Не указан ID платежа"
        })
    
    try:
        # Находим платеж
        payment = Payment.objects.get(id=payment_id)
        
        # Проверяем статус платежа в ЮКассе
        if payment.yookassa_payment_id:
            yookassa_status = check_yookassa_payment_status(payment.yookassa_payment_id)
            if yookassa_status:
                # Обновляем статус в нашей БД если нужно
                if yookassa_status == 'succeeded' and payment.status != Payment.Status.SUCCEEDED:
                    payment.status = Payment.Status.SUCCEEDED
                    payment.paid_at = timezone.now()
                    payment.save()
                    
                    # Отправляем уведомление в Telegram
                    try:
                        telegram_service = TelegramNotificationService()
                        telegram_service.send_payment_notification(payment)
                    except Exception as e:
                        print(f"Error sending Telegram notification: {e}")
        
        # Показываем соответствующую страницу в зависимости от статуса
        if payment.status == Payment.Status.SUCCEEDED:
            return render(request, "payments/success.html", {
                "payment": payment
            })
        elif payment.status == Payment.Status.CANCELED:
            return render(request, "payments/fail.html", {
                "error": "Платеж был отменен"
            })
        else:
            # Платеж еще в процессе
            return render(request, "payments/pending.html", {
                "payment": payment
            })
            
    except Payment.DoesNotExist:
        return render(request, "payments/fail.html", {
            "error": "Платеж не найден"
        })
    except Exception as e:
        print(f"Error in pay_success: {e}")
        return render(request, "payments/fail.html", {
            "error": "Ошибка обработки платежа"
        })

def pay_fail(request):
    """Страница неудачной оплаты"""
    error = request.GET.get('error', 'Произошла ошибка при обработке платежа')
    return render(request, "payments/fail.html", {
        "error": error
    })

@csrf_exempt
def yookassa_webhook(request):
    """Webhook от ЮКассы для обработки уведомлений о статусе платежа"""
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        # Получаем данные из webhook
        data = json.loads(request.body)
        
        # Проверяем тип события
        event_type = data.get('type')
        if event_type not in ['payment.succeeded', 'payment.canceled', 'payment.waiting_for_capture']:
            return HttpResponse("OK")
        
        # Получаем объект платежа
        payment_object = data.get('object', {})
        yookassa_payment_id = payment_object.get('id')
        
        if not yookassa_payment_id:
            return HttpResponseBadRequest("No payment ID")
        
        # Находим наш платеж
        try:
            payment = Payment.objects.get(yookassa_payment_id=yookassa_payment_id)
        except Payment.DoesNotExist:
            return HttpResponseBadRequest("Payment not found")
        
        # Обновляем статус
        if event_type == 'payment.succeeded':
            payment.status = Payment.Status.SUCCEEDED
            payment.paid_at = timezone.now()
            
            # Отправляем уведомление в Telegram
            try:
                telegram_service = TelegramNotificationService()
                telegram_service.send_payment_notification(payment)
            except Exception as e:
                print(f"Error sending Telegram notification: {e}")
                
        elif event_type == 'payment.canceled':
            payment.status = Payment.Status.CANCELED
            
        elif event_type == 'payment.waiting_for_capture':
            payment.status = Payment.Status.WAITING_FOR_CAPTURE
        
        # Сохраняем сырой ответ
        payment.raw_response = data
        payment.save()
        
        return HttpResponse("OK")
        
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    except Exception as e:
        print(f"Webhook error: {e}")
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
                    payment.save()
                    
                    # Отправляем уведомление в Telegram
                    try:
                        telegram_service = TelegramNotificationService()
                        telegram_service.send_payment_notification(payment)
                    except Exception as e:
                        print(f"Error sending Telegram notification: {e}")
                elif yookassa_status == 'canceled' and payment.status != Payment.Status.CANCELED:
                    payment.status = Payment.Status.CANCELED
                    payment.save()
                elif yookassa_status == 'waiting_for_capture' and payment.status != Payment.Status.WAITING_FOR_CAPTURE:
                    payment.status = Payment.Status.WAITING_FOR_CAPTURE
                    payment.save()
        
        return JsonResponse({
            "status": payment.status,
            "amount": str(payment.amount),
            "service_name": payment.service_name,
            "customer_fio": payment.customer_fio,
            "created": payment.created.isoformat(),
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None
        })
        
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)
    except Exception as e:
        print(f"Error checking payment status: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)