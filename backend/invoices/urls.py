"""
URL routing для Invoice API endpoints.

Структура:
- /api/invoices/tutor/ - endpoints для тьюторов
- /api/invoices/parent/ - endpoints для родителей
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import TutorInvoiceViewSet, ParentInvoiceViewSet

# Создаем роутеры для каждого ViewSet
tutor_router = DefaultRouter()
tutor_router.register(r'', TutorInvoiceViewSet, basename='tutor-invoice')

parent_router = DefaultRouter()
parent_router.register(r'', ParentInvoiceViewSet, basename='parent-invoice')

app_name = 'invoices'

urlpatterns = [
    # Tutor endpoints
    # GET /api/invoices/tutor/ - список счетов
    # POST /api/invoices/tutor/ - создать счет
    # GET /api/invoices/tutor/{id}/ - детальная информация
    # DELETE /api/invoices/tutor/{id}/ - отменить счет
    # POST /api/invoices/tutor/{id}/send/ - отправить счет
    path('tutor/', include(tutor_router.urls)),

    # Parent endpoints
    # GET /api/invoices/parent/ - список счетов
    # GET /api/invoices/parent/{id}/ - детальная информация
    # POST /api/invoices/parent/{id}/mark_viewed/ - отметить просмотренным
    # POST /api/invoices/parent/{id}/pay/ - инициировать оплату
    path('parent/', include(parent_router.urls)),
]
