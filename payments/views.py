# payments/views.py
from decimal import Decimal
import hashlib

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt

from .models import Payment

SUCCESS_URL = "/payments/success/"
FAIL_URL = "/payments/fail/"

def pay_page(request):
    if request.method == "POST":
        service_name = (request.POST.get("service_name") or "").strip()
        customer_fio = (request.POST.get("customer_fio") or "").strip()
        raw_amount = (request.POST.get("amount") or "0").replace(",", ".")
        try:
            amount = Decimal(raw_amount)
        except Exception:
            return HttpResponseBadRequest("bad amount")
        if not service_name or not customer_fio or amount <= 0:
            return HttpResponseBadRequest("fill all fields correctly")

        label = f"pay_{get_random_string(12)}"
        p = Payment.objects.create(
            label=label,
            amount=amount,
            service_name=service_name,
            customer_fio=customer_fio,
        )

        return render(request, "payments/redirect_form.html", {
            "receiver": settings.YOOMONEY_RECEIVER,
            "label": p.label,
            "amount": p.amount,
            "targets": f"{p.service_name} — {p.customer_fio}",
            "comment": f"Услуга: {p.service_name}; Плательщик: {p.customer_fio}",
            "success_url": request.build_absolute_uri(SUCCESS_URL),
            "fail_url": request.build_absolute_uri(FAIL_URL),
        })
    return render(request, "payments/pay.html")

def pay_success(request):
    return render(request, "payments/success.html")

def pay_fail(request):
    return render(request, "payments/fail.html")

@csrf_exempt
def notify(request):
    """Webhook от YooMoney — обновляем статус платежа по подписи."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    data = {k: request.POST.get(k, "") for k in [
        "notification_type","operation_id","amount","currency",
        "datetime","sender","codepro","label","sha1_hash"
    ]}

    to_sign = "&".join([
        data["notification_type"],
        data["operation_id"],
        data["amount"],
        data["currency"],
        data["datetime"],
        data["sender"],
        data["codepro"],
        settings.YOOMONEY_SECRET,
        data["label"],
    ])
    digest = hashlib.sha1(to_sign.encode("utf-8")).hexdigest()
    if digest != data["sha1_hash"]:
        return HttpResponseBadRequest("bad signature")

    try:
        p = Payment.objects.get(label=data["label"])
    except Payment.DoesNotExist:
        return HttpResponseBadRequest("unknown label")

    p.status = Payment.Status.FAILED if data["codepro"] == "true" else Payment.Status.PAID
    p.operation_id = data["operation_id"]
    p.payer = data["sender"]
    p.raw = data
    p.save(update_fields=["status","operation_id","payer","raw","updated"])
    return HttpResponse("OK")

