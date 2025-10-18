import hashlib
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from .models import Payment

SUCCESS_URL = "/payments/success/"
FAIL_URL = "/payments/fail/"

def pay_page(request):
    if request.method == "POST":
        raw = request.POST.get("amount", "0").replace(",", ".")
        try:
            amount = Decimal(raw)
        except Exception:
            return HttpResponseBadRequest("bad amount")
        if amount <= 0:
            return HttpResponseBadRequest("amount must be > 0")

        label = f"pay_{get_random_string(12)}"
        p = Payment.objects.create(label=label, amount=amount)

        return render(request, "payments/redirect_form.html", {
            "receiver": settings.YOOMONEY_RECEIVER,
            "label": p.label,
            "amount": p.amount,
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
