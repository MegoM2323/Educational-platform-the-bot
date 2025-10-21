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
            payment.return_url = request.build_absolute_uri(SUCCESS_URL)
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
            "return_url": request.build_absolute_uri(SUCCESS_URL)
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

def pay_success(request):
    """Страница успешной оплаты"""
    return render(request, "payments/success.html")

def pay_fail(request):
    """Страница неудачной оплаты"""
    return render(request, "payments/fail.html")

@csrf_exempt
def yookassa_webhook(request):
    """Webhook от ЮКассы для обработки уведомлений о статусе платежа"""
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        # Получаем данные из webhook
        data = json.loads(request.body)
        
        # Проверяем тип события
        if data.get('type') != 'payment.succeeded' and data.get('type') != 'payment.canceled':
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
        if data.get('type') == 'payment.succeeded':
            payment.status = Payment.Status.SUCCEEDED
            payment.paid_at = timezone.now()
            
            # Отправляем уведомление в Telegram
            try:
                telegram_service = TelegramNotificationService()
                telegram_service.send_payment_notification(payment)
            except Exception as e:
                print(f"Error sending Telegram notification: {e}")
                
        elif data.get('type') == 'payment.canceled':
            payment.status = Payment.Status.CANCELED
        
        # Сохраняем сырой ответ
        payment.raw_response = data
        payment.save()
        
        return HttpResponse("OK")
        
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")
    except Exception as e:
        print(f"Webhook error: {e}")
        return HttpResponseBadRequest("Error processing webhook")