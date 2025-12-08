"""
API views для управления счетами.

ViewSets:
- TutorInvoiceViewSet: управление счетами для тьюторов (CRUD + send)
- ParentInvoiceViewSet: просмотр и оплата счетов для родителей (read-only + pay)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from datetime import datetime

from .models import Invoice
from .serializers import (
    InvoiceSerializer,
    InvoiceListSerializer,
    CreateInvoiceSerializer,
    SendInvoiceSerializer,
    ViewInvoiceSerializer,
    TutorStatisticsSerializer,
    PaymentHistoryItemSerializer,
    RevenueReportSerializer,
    OutstandingInvoiceSerializer
)
from .services import InvoiceService
from .reports import InvoiceReportService
from .permissions import IsTutorOrParent, IsTutorForStudent, IsParentOfStudent
from .exceptions import (
    InvoicePermissionDenied,
    InvoiceNotFound,
    InvalidInvoiceStatus,
    DuplicateInvoiceError
)


class TutorInvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления счетами тьютором.

    Endpoints:
    - GET /api/invoices/tutor/ - список счетов тьютора
    - POST /api/invoices/tutor/ - создать новый счет
    - GET /api/invoices/tutor/{id}/ - детальная информация о счете
    - DELETE /api/invoices/tutor/{id}/ - отменить счет
    - POST /api/invoices/tutor/{id}/send/ - отправить счет родителю

    Фильтры:
    - status: фильтр по статусу (draft, sent, viewed, paid, cancelled, overdue)
    - student_id: фильтр по ID студента
    - from_date: начальная дата создания (ISO format: YYYY-MM-DD)
    - to_date: конечная дата создания (ISO format: YYYY-MM-DD)

    Сортировка:
    - ordering: сортировка (-created_at, amount, due_date)

    Пагинация:
    - page_size: количество элементов на странице (по умолчанию 20)
    - page: номер страницы
    """

    serializer_class = InvoiceListSerializer
    permission_classes = [IsAuthenticated, IsTutorOrParent]
    pagination_class = None  # Используем custom pagination

    def get_queryset(self):
        """Получение счетов тьютора с оптимизацией запросов"""
        user = self.request.user

        # Только тьюторы могут использовать этот ViewSet
        if user.role != 'tutor':
            return Invoice.objects.none()

        # Получаем фильтры из query params
        filters = {}

        status_param = self.request.query_params.get('status')
        if status_param:
            filters['status'] = status_param

        student_id_param = self.request.query_params.get('student_id')
        if student_id_param:
            filters['student_id'] = int(student_id_param)

        from_date_param = self.request.query_params.get('from_date')
        if from_date_param:
            filters['date_from'] = from_date_param

        to_date_param = self.request.query_params.get('to_date')
        if to_date_param:
            filters['date_to'] = to_date_param

        # Используем сервисный слой для получения queryset
        queryset = InvoiceService.get_tutor_invoices(user, filters)

        # Применяем сортировку
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Список счетов тьютора с пагинацией.

        GET /api/invoices/tutor/?page=1&page_size=20&status=sent&ordering=-created_at
        """
        queryset = self.get_queryset()

        # Пагинация
        page_size = int(request.query_params.get('page_size', 20))
        page_number = int(request.query_params.get('page', 1))

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)

        serializer = self.get_serializer(page_obj.object_list, many=True)

        return Response({
            'success': True,
            'data': {
                'results': serializer.data,
                'count': paginator.count,
                'page': page_number,
                'page_size': page_size,
                'total_pages': paginator.num_pages
            }
        })

    def create(self, request, *args, **kwargs):
        """
        Создание нового счета.

        POST /api/invoices/tutor/
        {
            "student_id": 123,
            "amount": "5000.00",
            "description": "Услуги по математике за декабрь",
            "due_date": "2025-01-10",
            "enrollment_id": 456  // optional
        }
        """
        # Только тьюторы могут создавать счета
        if request.user.role != 'tutor':
            return Response(
                {
                    'success': False,
                    'error': 'Только тьюторы могут создавать счета',
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Валидация входных данных
        serializer = CreateInvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'error': serializer.errors,
                    'code': 'VALIDATION_ERROR'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Создаем счет через сервисный слой
            invoice = InvoiceService.create_invoice(
                tutor=request.user,
                student_id=serializer.validated_data['student_id'],
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data['description'],
                due_date=serializer.validated_data['due_date'],
                enrollment_id=serializer.validated_data.get('enrollment_id')
            )

            # Возвращаем созданный счет
            output_serializer = InvoiceSerializer(invoice)
            return Response(
                {
                    'success': True,
                    'data': output_serializer.data,
                    'message': 'Счет успешно создан'
                },
                status=status.HTTP_201_CREATED
            )

        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except DuplicateInvoiceError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'DUPLICATE_INVOICE'
                },
                status=status.HTTP_409_CONFLICT
            )
        except DjangoValidationError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'VALIDATION_ERROR'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, pk=None):
        """
        Получение детальной информации о счете.

        GET /api/invoices/tutor/{id}/
        """
        try:
            invoice = InvoiceService.get_invoice_detail(invoice_id=pk, user=request.user)
            serializer = InvoiceSerializer(invoice)
            return Response({
                'success': True,
                'data': serializer.data
            })

        except InvoiceNotFound as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

    def destroy(self, request, pk=None):
        """
        Отмена счета (soft delete).

        DELETE /api/invoices/tutor/{id}/
        """
        try:
            reason = request.data.get('reason', '')
            invoice = InvoiceService.cancel_invoice(
                invoice_id=pk,
                user=request.user,
                reason=reason
            )

            return Response({
                'success': True,
                'data': {
                    'id': invoice.id,
                    'status': invoice.status,
                    'message': 'Счет успешно отменен'
                }
            })

        except InvoiceNotFound as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except InvalidInvoiceStatus as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_STATUS'
                },
                status=status.HTTP_409_CONFLICT
            )

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        """
        Отправка счета родителю.

        POST /api/invoices/tutor/{id}/send/

        Изменяет статус с DRAFT → SENT и триггерит уведомления.
        """
        try:
            invoice = InvoiceService.send_invoice(invoice_id=pk, tutor=request.user)

            return Response({
                'success': True,
                'data': {
                    'id': invoice.id,
                    'status': invoice.status,
                    'sent_at': invoice.sent_at.isoformat() if invoice.sent_at else None,
                    'message': 'Счет успешно отправлен родителю'
                }
            })

        except InvoiceNotFound as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except InvalidInvoiceStatus as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_STATUS'
                },
                status=status.HTTP_409_CONFLICT
            )

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Получение статистики по счетам тьютора.

        GET /api/invoices/tutor/statistics/?period=month

        Query params:
        - period: week | month | quarter | year | all (default: month)

        Response:
        {
            "success": true,
            "data": {
                "period": "month",
                "statistics": {
                    "total_invoices": 15,
                    "total_amount": "75000.00",
                    "total_paid": "65000.00",
                    "average_invoice": "5000.00",
                    "payment_rate": 86.67,
                    "students_invoiced": 8,
                    "due_count": 2,
                    "overdue_count": 1,
                    "pending_count": 2
                }
            }
        }
        """
        # Только тьюторы могут использовать этот endpoint
        if request.user.role != 'tutor':
            return Response(
                {
                    'success': False,
                    'error': 'Только тьюторы могут просматривать статистику',
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем период из query params
        period = request.query_params.get('period', InvoiceReportService.PERIOD_MONTH)

        # Валидация периода
        valid_periods = [
            InvoiceReportService.PERIOD_WEEK,
            InvoiceReportService.PERIOD_MONTH,
            InvoiceReportService.PERIOD_QUARTER,
            InvoiceReportService.PERIOD_YEAR,
            InvoiceReportService.PERIOD_ALL
        ]
        if period not in valid_periods:
            return Response(
                {
                    'success': False,
                    'error': f'Неверный период. Допустимые значения: {", ".join(valid_periods)}',
                    'code': 'INVALID_PERIOD'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Получаем статистику через сервис
            statistics = InvoiceReportService.get_tutor_statistics(request.user, period)

            serializer = TutorStatisticsSerializer(statistics)
            return Response({
                'success': True,
                'data': serializer.data
            })

        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=False, methods=['get'], url_path='revenue')
    def revenue(self, request):
        """
        Получение отчета по выручке за период.

        GET /api/invoices/tutor/revenue/?start_date=2025-12-01&end_date=2025-12-31

        Query params:
        - start_date: YYYY-MM-DD (required)
        - end_date: YYYY-MM-DD (required)

        Response:
        {
            "success": true,
            "data": {
                "period": {
                    "start_date": "2025-12-01",
                    "end_date": "2025-12-31"
                },
                "summary": {
                    "paid_revenue": "65000.00",
                    "pending_revenue": "10000.00",
                    "overdue_revenue": "2000.00"
                },
                "breakdown": [
                    {
                        "date": "2025-12-08",
                        "amount": "5000.00",
                        "count": 1
                    }
                ]
            }
        }
        """
        # Только тьюторы могут использовать этот endpoint
        if request.user.role != 'tutor':
            return Response(
                {
                    'success': False,
                    'error': 'Только тьюторы могут просматривать отчеты по выручке',
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем и валидируем параметры
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not start_date_str or not end_date_str:
            return Response(
                {
                    'success': False,
                    'error': 'Параметры start_date и end_date обязательны',
                    'code': 'MISSING_PARAMETERS'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {
                    'success': False,
                    'error': 'Неверный формат даты. Используйте YYYY-MM-DD',
                    'code': 'INVALID_DATE_FORMAT'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Валидация диапазона дат
        if start_date > end_date:
            return Response(
                {
                    'success': False,
                    'error': 'start_date не может быть позже end_date',
                    'code': 'INVALID_DATE_RANGE'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Получаем отчет через сервис
            report = InvoiceReportService.get_revenue_report(
                request.user,
                start_date,
                end_date
            )

            serializer = RevenueReportSerializer(report)
            return Response({
                'success': True,
                'data': serializer.data
            })

        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=False, methods=['get'], url_path='outstanding')
    def outstanding(self, request):
        """
        Получение списка неоплаченных счетов.

        GET /api/invoices/tutor/outstanding/

        Response:
        {
            "success": true,
            "data": {
                "invoices": [
                    {
                        "id": 5,
                        "student_name": "Петр Иванов",
                        "parent_name": "Мария Иванова",
                        "amount": "2000.00",
                        "status": "overdue",
                        "status_display": "Просрочен",
                        "due_date": "2025-12-05",
                        "days_overdue": 3,
                        "created_at": "2025-12-01T10:00:00Z"
                    }
                ]
            }
        }
        """
        # Только тьюторы могут использовать этот endpoint
        if request.user.role != 'tutor':
            return Response(
                {
                    'success': False,
                    'error': 'Только тьюторы могут просматривать неоплаченные счета',
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Получаем queryset через сервис
            queryset = InvoiceReportService.get_outstanding_invoices(request.user)

            # Сериализуем
            serializer = OutstandingInvoiceSerializer(queryset, many=True)

            return Response({
                'success': True,
                'data': {
                    'invoices': serializer.data
                }
            })

        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=False, methods=['post'], url_path='export')
    def export(self, request):
        """
        Экспорт счетов в CSV.

        POST /api/invoices/tutor/export/
        {
            "filters": {
                "status": "paid",
                "start_date": "2025-12-01",
                "end_date": "2025-12-31"
            }
        }

        Returns CSV file for download.
        """
        # Только тьюторы могут использовать этот endpoint
        if request.user.role != 'tutor':
            return Response(
                {
                    'success': False,
                    'error': 'Только тьюторы могут экспортировать счета',
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Получаем фильтры из тела запроса
            filters = request.data.get('filters', {})

            # Используем существующий метод get_tutor_invoices с фильтрами
            queryset = InvoiceService.get_tutor_invoices(request.user, filters)

            # Экспортируем в CSV
            csv_output = InvoiceReportService.export_to_csv(queryset)

            # Создаем HTTP response с CSV
            response = HttpResponse(csv_output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="invoices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'

            return response

        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Export failed: {e}')

            return Response(
                {
                    'success': False,
                    'error': 'Ошибка при экспорте данных',
                    'code': 'EXPORT_ERROR'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ParentInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра и оплаты счетов родителем.

    Endpoints:
    - GET /api/invoices/parent/ - список счетов родителя
    - GET /api/invoices/parent/{id}/ - детальная информация о счете
    - POST /api/invoices/parent/{id}/mark_viewed/ - отметить счет просмотренным
    - POST /api/invoices/parent/{id}/pay/ - инициировать оплату через YooKassa

    Фильтры:
    - status: фильтр по статусу
    - child_id: фильтр по ID ребенка
    - from_date: начальная дата создания
    - to_date: конечная дата создания
    - unpaid_only: только неоплаченные счета (true/false)

    Сортировка:
    - ordering: сортировка (-due_date, -created_at, amount)

    Пагинация:
    - page_size: количество элементов на странице (по умолчанию 20)
    - page: номер страницы
    """

    serializer_class = InvoiceListSerializer
    permission_classes = [IsAuthenticated, IsTutorOrParent]
    pagination_class = None  # Используем custom pagination

    def get_queryset(self):
        """Получение счетов родителя с оптимизацией запросов"""
        user = self.request.user

        # Только родители могут использовать этот ViewSet
        if user.role != 'parent':
            return Invoice.objects.none()

        # Получаем фильтры из query params
        filters = {}

        status_param = self.request.query_params.get('status')
        if status_param:
            filters['status'] = status_param

        child_id_param = self.request.query_params.get('child_id')
        if child_id_param:
            filters['child_id'] = int(child_id_param)

        from_date_param = self.request.query_params.get('from_date')
        if from_date_param:
            filters['date_from'] = from_date_param

        to_date_param = self.request.query_params.get('to_date')
        if to_date_param:
            filters['date_to'] = to_date_param

        unpaid_only_param = self.request.query_params.get('unpaid_only')
        if unpaid_only_param and unpaid_only_param.lower() == 'true':
            filters['unpaid_only'] = True

        # Используем сервисный слой для получения queryset
        queryset = InvoiceService.get_parent_invoices(user, filters)

        # Применяем сортировку
        ordering = self.request.query_params.get('ordering', '-due_date')
        queryset = queryset.order_by(ordering)

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Список счетов родителя с пагинацией.

        GET /api/invoices/parent/?page=1&page_size=20&unpaid_only=true&ordering=-due_date
        """
        queryset = self.get_queryset()

        # Пагинация
        page_size = int(request.query_params.get('page_size', 20))
        page_number = int(request.query_params.get('page', 1))

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page_number)

        serializer = self.get_serializer(page_obj.object_list, many=True)

        return Response({
            'success': True,
            'data': {
                'results': serializer.data,
                'count': paginator.count,
                'page': page_number,
                'page_size': page_size,
                'total_pages': paginator.num_pages
            }
        })

    def retrieve(self, request, pk=None):
        """
        Получение детальной информации о счете.

        GET /api/invoices/parent/{id}/
        """
        try:
            invoice = InvoiceService.get_invoice_detail(invoice_id=pk, user=request.user)
            serializer = InvoiceSerializer(invoice)
            return Response({
                'success': True,
                'data': serializer.data
            })

        except InvoiceNotFound as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['post'], url_path='mark_viewed')
    def mark_viewed(self, request, pk=None):
        """
        Отметка счета как просмотренного.

        POST /api/invoices/parent/{id}/mark_viewed/

        Изменяет статус с SENT → VIEWED.
        """
        try:
            invoice = InvoiceService.mark_invoice_viewed(invoice_id=pk, parent=request.user)

            return Response({
                'success': True,
                'data': {
                    'id': invoice.id,
                    'status': invoice.status,
                    'viewed_at': invoice.viewed_at.isoformat() if invoice.viewed_at else None,
                    'message': 'Счет отмечен как просмотренный'
                }
            })

        except InvoiceNotFound as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        except InvalidInvoiceStatus as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'INVALID_STATUS'
                },
                status=status.HTTP_409_CONFLICT
            )

    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """
        Получение истории платежей родителя.

        GET /api/invoices/parent/history/?period=month

        Query params:
        - period: week | month | quarter | year | all (default: all)

        Response:
        {
            "success": true,
            "data": {
                "payments": [
                    {
                        "id": 1,
                        "student_name": "Иван Петров",
                        "tutor_name": "Анна Смирнова",
                        "subject_name": "Математика",
                        "amount": "5000.00",
                        "status": "paid",
                        "status_display": "Оплачен",
                        "paid_at": "2025-12-01T15:30:00Z",
                        "description": "Оплата за 4 занятия",
                        "due_date": "2025-12-10",
                        "created_at": "2025-11-25T10:00:00Z"
                    }
                ]
            }
        }
        """
        # Только родители могут использовать этот endpoint
        if request.user.role != 'parent':
            return Response(
                {
                    'success': False,
                    'error': 'Только родители могут просматривать историю платежей',
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Получаем период из query params
        period = request.query_params.get('period', InvoiceReportService.PERIOD_ALL)

        # Валидация периода
        valid_periods = [
            InvoiceReportService.PERIOD_WEEK,
            InvoiceReportService.PERIOD_MONTH,
            InvoiceReportService.PERIOD_QUARTER,
            InvoiceReportService.PERIOD_YEAR,
            InvoiceReportService.PERIOD_ALL
        ]
        if period not in valid_periods:
            return Response(
                {
                    'success': False,
                    'error': f'Неверный период. Допустимые значения: {", ".join(valid_periods)}',
                    'code': 'INVALID_PERIOD'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Получаем историю через сервис
            queryset = InvoiceReportService.get_payment_history(request.user, period)

            # Пагинация
            page_size = int(request.query_params.get('page_size', 20))
            page_number = int(request.query_params.get('page', 1))

            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page_number)

            # Сериализуем
            serializer = PaymentHistoryItemSerializer(page_obj.object_list, many=True)

            return Response({
                'success': True,
                'data': {
                    'payments': serializer.data,
                    'count': paginator.count,
                    'page': page_number,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages
                }
            })

        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )

    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        """
        Инициирование оплаты счета через YooKassa.

        POST /api/invoices/parent/{id}/pay/

        Возвращает URL для редиректа на страницу оплаты YooKassa.

        Response:
        {
            "success": true,
            "data": {
                "payment_url": "https://yookassa.ru/...",
                "payment_id": "2c66e...",
                "invoice_id": 123,
                "amount": "5000.00"
            }
        }
        """
        try:
            # Получаем счет
            invoice = InvoiceService.get_invoice_detail(invoice_id=pk, user=request.user)

            # Проверка что счет можно оплатить
            if invoice.status == Invoice.Status.PAID:
                return Response(
                    {
                        'success': False,
                        'error': 'Счет уже оплачен',
                        'code': 'ALREADY_PAID'
                    },
                    status=status.HTTP_409_CONFLICT
                )

            if invoice.status == Invoice.Status.CANCELLED:
                return Response(
                    {
                        'success': False,
                        'error': 'Невозможно оплатить отмененный счет',
                        'code': 'CANCELLED'
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Создаем платеж через YooKassa
            from payments.services import create_invoice_payment
            from .exceptions import InvoicePaymentError

            try:
                payment = create_invoice_payment(
                    invoice=invoice,
                    user=request.user,
                    request=request
                )

                # Возвращаем данные для редиректа
                return Response({
                    'success': True,
                    'data': {
                        'payment_url': payment.confirmation_url,
                        'payment_id': str(payment.id),
                        'yookassa_payment_id': payment.yookassa_payment_id,
                        'invoice_id': invoice.id,
                        'amount': str(invoice.amount),
                        'status': payment.status
                    }
                }, status=status.HTTP_200_OK)

            except InvoicePaymentError as e:
                return Response(
                    {
                        'success': False,
                        'error': str(e),
                        'code': 'PAYMENT_ERROR'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except InvoiceNotFound as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'NOT_FOUND'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except InvoicePermissionDenied as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'PERMISSION_DENIED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
