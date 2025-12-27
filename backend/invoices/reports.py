"""
Invoice Reporting and Analytics Service

Provides statistical reports, revenue analysis, and CSV export functionality
for tutors and parents to track invoice and payment data.
"""
import csv
import io
import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import date, datetime, timedelta

from django.db.models import QuerySet, Sum, Count, Avg, Q, F
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Invoice
from .exceptions import InvoicePermissionDenied

User = get_user_model()
logger = logging.getLogger(__name__)


class InvoiceReportService:
    """
    Сервис для генерации отчетов и аналитики по счетам

    Функциональность:
    - Статистика для тьюторов (общая сводка)
    - История платежей для родителей
    - Отчет по выручке с временными периодами
    - Список просроченных счетов
    - Экспорт данных в CSV
    """

    # Периоды для статистики
    PERIOD_WEEK = 'week'
    PERIOD_MONTH = 'month'
    PERIOD_QUARTER = 'quarter'
    PERIOD_YEAR = 'year'
    PERIOD_ALL = 'all'

    @staticmethod
    def _get_period_dates(period: str) -> tuple[date, date]:
        """
        Получение дат начала и конца периода

        Args:
            period: Период (week, month, quarter, year, all)

        Returns:
            Кортеж (start_date, end_date)
        """
        today = timezone.now().date()

        if period == InvoiceReportService.PERIOD_WEEK:
            start_date = today - timedelta(days=7)
        elif period == InvoiceReportService.PERIOD_MONTH:
            start_date = today - timedelta(days=30)
        elif period == InvoiceReportService.PERIOD_QUARTER:
            start_date = today - timedelta(days=90)
        elif period == InvoiceReportService.PERIOD_YEAR:
            start_date = today - timedelta(days=365)
        else:  # all
            start_date = date(2000, 1, 1)

        return start_date, today

    @staticmethod
    def get_tutor_statistics(tutor: User, period: str = PERIOD_MONTH) -> Dict[str, Any]:
        """
        Получение сводной статистики для тьютора

        Включает:
        - Общее количество счетов
        - Общая сумма выставленных счетов
        - Общая сумма оплаченных счетов
        - Средняя сумма счета
        - Процент оплаты
        - Количество студентов с счетами
        - Количество счетов по статусам

        Args:
            tutor: Пользователь с ролью 'tutor'
            period: Период для статистики

        Returns:
            Словарь со статистикой

        Raises:
            InvoicePermissionDenied: Если пользователь не тьютор
        """
        if tutor.role != 'tutor':
            raise InvoicePermissionDenied('Только тьюторы могут просматривать статистику')

        # Проверяем кеш (срок жизни 1 час)
        cache_key = f'invoice_stats_{tutor.id}_{period}'
        cached_stats = cache.get(cache_key)
        if cached_stats is not None:
            logger.debug(f'Statistics cache hit for tutor {tutor.id}, period {period}')
            return cached_stats

        logger.info(f'Generating statistics for tutor {tutor.id}, period {period}')

        # Получаем даты периода
        start_date, end_date = InvoiceReportService._get_period_dates(period)

        # Базовый queryset с фильтром по периоду
        queryset = Invoice.objects.filter(
            tutor=tutor,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        # Агрегированные данные
        aggregates = queryset.aggregate(
            total_invoices=Count('id'),
            total_amount=Sum('amount'),
            total_paid=Sum('amount', filter=Q(status=Invoice.Status.PAID)),
            average_invoice=Avg('amount'),
            students_count=Count('student', distinct=True)
        )

        # Количество счетов по статусам
        due_count = queryset.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED]
        ).count()

        overdue_count = queryset.filter(status=Invoice.Status.OVERDUE).count()

        pending_count = queryset.filter(status=Invoice.Status.DRAFT).count()

        # Расчет процента оплаты
        total_amount = aggregates['total_amount'] or Decimal('0')
        total_paid = aggregates['total_paid'] or Decimal('0')

        payment_rate = (
            float(total_paid / total_amount * 100)
            if total_amount > 0
            else 0.0
        )

        statistics = {
            'period': period,
            'statistics': {
                'total_invoices': aggregates['total_invoices'] or 0,
                'total_amount': str(total_amount),
                'total_paid': str(total_paid),
                'average_invoice': str(aggregates['average_invoice'] or Decimal('0')),
                'payment_rate': round(payment_rate, 2),
                'students_invoiced': aggregates['students_count'] or 0,
                'due_count': due_count,
                'overdue_count': overdue_count,
                'pending_count': pending_count
            }
        }

        # Кешируем на 1 час
        cache.set(cache_key, statistics, 3600)

        return statistics

    @staticmethod
    def get_payment_history(parent: User, period: str = PERIOD_ALL) -> QuerySet[Invoice]:
        """
        Получение истории платежей для родителя

        Возвращает только оплаченные счета, отсортированные по дате оплаты.

        Args:
            parent: Пользователь с ролью 'parent'
            period: Период фильтрации

        Returns:
            QuerySet с оплаченными счетами

        Raises:
            InvoicePermissionDenied: Если пользователь не родитель
        """
        if parent.role != 'parent':
            raise InvoicePermissionDenied('Только родители могут просматривать историю платежей')

        # Получаем даты периода
        start_date, end_date = InvoiceReportService._get_period_dates(period)

        # Queryset оплаченных счетов с оптимизацией
        queryset = Invoice.objects.filter(
            parent=parent,
            status=Invoice.Status.PAID,
            paid_at__date__gte=start_date,
            paid_at__date__lte=end_date
        ).select_related(
            'tutor',
            'student',
            'payment',
            'enrollment',
            'enrollment__subject'
        ).order_by('-paid_at')

        return queryset

    @staticmethod
    def get_revenue_report(
        tutor: User,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Получение отчета по выручке за период с детализацией

        Включает:
        - Общая выручка (оплаченные счета)
        - Ожидаемая выручка (отправленные, но не оплаченные)
        - Просроченная выручка (просроченные счета)
        - Разбивка по дням/неделям/месяцам

        Args:
            tutor: Пользователь с ролью 'tutor'
            start_date: Начальная дата
            end_date: Конечная дата

        Returns:
            Словарь с отчетом по выручке

        Raises:
            InvoicePermissionDenied: Если пользователь не тьютор
            ValidationError: Если start_date > end_date
        """
        if tutor.role != 'tutor':
            raise InvoicePermissionDenied('Только тьюторы могут просматривать отчеты по выручке')

        # Валидация диапазона дат
        if start_date > end_date:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f'Начальная дата ({start_date}) не может быть позже конечной даты ({end_date})'
            )

        # Проверяем кеш (срок жизни 30 минут)
        cache_key = f'revenue_report_{tutor.id}_{start_date}_{end_date}'
        cached_report = cache.get(cache_key)
        if cached_report is not None:
            logger.debug(f'Revenue report cache hit for tutor {tutor.id}')
            return cached_report

        logger.info(f'Generating revenue report for tutor {tutor.id}, {start_date} to {end_date}')

        # Базовый queryset
        queryset = Invoice.objects.filter(
            tutor=tutor,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )

        # Агрегация по типам выручки
        paid_revenue = queryset.filter(
            status=Invoice.Status.PAID
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        pending_revenue = queryset.filter(
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        overdue_revenue = queryset.filter(
            status=Invoice.Status.OVERDUE
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Разбивка по датам (группировка по дате оплаты для paid invoices)
        daily_breakdown = []
        paid_invoices = queryset.filter(status=Invoice.Status.PAID).values(
            'paid_at__date'
        ).annotate(
            amount=Sum('amount'),
            count=Count('id')
        ).order_by('paid_at__date')

        for item in paid_invoices:
            if item['paid_at__date']:
                daily_breakdown.append({
                    'date': item['paid_at__date'].isoformat(),
                    'amount': str(item['amount']),
                    'count': item['count']
                })

        report = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'paid_revenue': str(paid_revenue),
                'pending_revenue': str(pending_revenue),
                'overdue_revenue': str(overdue_revenue)
            },
            'breakdown': daily_breakdown
        }

        # Кешируем на 30 минут
        cache.set(cache_key, report, 1800)

        return report

    @staticmethod
    def get_outstanding_invoices(tutor: User) -> QuerySet[Invoice]:
        """
        Получение списка неоплаченных счетов

        Включает счета со статусами sent, viewed, overdue.
        Сортирует по due_date (просроченные первыми).

        Args:
            tutor: Пользователь с ролью 'tutor'

        Returns:
            QuerySet с неоплаченными счетами

        Raises:
            InvoicePermissionDenied: Если пользователь не тьютор
        """
        if tutor.role != 'tutor':
            raise InvoicePermissionDenied('Только тьюторы могут просматривать неоплаченные счета')

        today = timezone.now().date()

        # Queryset неоплаченных счетов
        queryset = Invoice.objects.filter(
            tutor=tutor,
            status__in=[Invoice.Status.SENT, Invoice.Status.VIEWED, Invoice.Status.OVERDUE]
        ).select_related(
            'student',
            'parent',
            'enrollment',
            'enrollment__subject'
        ).annotate(
            # Вычисляем количество дней просрочки
            days_overdue=F('due_date')
        ).order_by('due_date')  # Сначала самые срочные

        return queryset

    @staticmethod
    def export_to_csv(queryset: QuerySet[Invoice], filename: str = 'invoices.csv') -> io.StringIO:
        """
        Экспорт счетов в CSV формат

        Включает все релевантные поля для анализа.

        Args:
            queryset: QuerySet счетов для экспорта
            filename: Имя файла (не используется, но сохраняется для совместимости)

        Returns:
            StringIO объект с CSV содержимым
        """
        logger.info(f'Exporting {queryset.count()} invoices to CSV')

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)

        # Заголовки
        headers = [
            'Invoice ID',
            'Student',
            'Parent',
            'Amount (RUB)',
            'Status',
            'Due Date',
            'Sent Date',
            'Viewed Date',
            'Paid Date',
            'Description',
            'Subject',
            'Created At'
        ]
        writer.writerow(headers)

        # Оптимизация: предзагрузка связанных объектов
        queryset = queryset.select_related(
            'student',
            'parent',
            'enrollment',
            'enrollment__subject'
        )

        # Данные
        for invoice in queryset:
            row = [
                invoice.id,
                invoice.student.get_full_name(),
                invoice.parent.get_full_name(),
                str(invoice.amount),
                invoice.get_status_display(),
                invoice.due_date.isoformat() if invoice.due_date else '',
                invoice.sent_at.isoformat() if invoice.sent_at else '',
                invoice.viewed_at.isoformat() if invoice.viewed_at else '',
                invoice.paid_at.isoformat() if invoice.paid_at else '',
                # Экранируем описание (удаляем переносы строк)
                invoice.description.replace('\n', ' ').replace('\r', ' ')[:200],
                invoice.enrollment.subject.name if invoice.enrollment else '',
                invoice.created_at.isoformat()
            ]
            writer.writerow(row)

        # Возвращаем в начало потока
        output.seek(0)
        return output

    @staticmethod
    def invalidate_cache(tutor: User) -> None:
        """
        Инвалидация кеша статистики и отчетов для тьютора

        Вызывается при изменении статуса счета или создании/удалении счета.

        Args:
            tutor: Пользователь с ролью 'tutor'
        """
        logger.info(f'Invalidating cache for tutor {tutor.id}')

        # Инвалидируем все периоды статистики
        for period in [
            InvoiceReportService.PERIOD_WEEK,
            InvoiceReportService.PERIOD_MONTH,
            InvoiceReportService.PERIOD_QUARTER,
            InvoiceReportService.PERIOD_YEAR,
            InvoiceReportService.PERIOD_ALL
        ]:
            cache_key = f'invoice_stats_{tutor.id}_{period}'
            cache.delete(cache_key)

        # Инвалидируем revenue reports (сложнее - удаляем по паттерну)
        # В production лучше использовать cache tags или Redis pattern matching
        # Здесь простое решение - удаляем последние 365 дней
        today = timezone.now().date()
        for days_ago in range(365):
            start_date = today - timedelta(days=days_ago)
            for days_ahead in range(30):  # Проверяем периоды до 30 дней
                end_date = start_date + timedelta(days=days_ahead)
                cache_key = f'revenue_report_{tutor.id}_{start_date}_{end_date}'
                cache.delete(cache_key)
