from django.contrib import admin
from django.urls import path
from payments.views import pay_page, notify, pay_success, pay_fail

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", pay_page, name="pay_page"),
    path("payments/notify/", notify, name="payments_notify"),
    path("payments/success/", pay_success, name="payments_success"),
    path("payments/fail/", pay_fail, name="payments_fail"),
]
