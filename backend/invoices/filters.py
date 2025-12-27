"""
Фильтры для Invoice API endpoints.

Предоставляет расширенные возможности фильтрации счетов:
- По статусу (множественный выбор)
- По диапазону дат (from_date, to_date)
- По студенту/ребенку
- По просроченным счетам
"""

from django_filters import rest_framework as filters
from django.utils import timezone

from .models import Invoice


class InvoiceFilter(filters.FilterSet):
    """
    Фильтр для счетов.

    Параметры:
    - status: множественный выбор статусов (draft, sent, viewed, paid, cancelled, overdue)
    - student_id: ID студента
    - from_date: начальная дата создания (YYYY-MM-DD)
    - to_date: конечная дата создания (YYYY-MM-DD)
    - overdue_only: только просроченные счета (true/false)
    - unpaid_only: только неоплаченные счета (true/false)
    """

    # Множественный выбор статусов
    status = filters.MultipleChoiceFilter(
        choices=Invoice.Status.choices,
        field_name='status',
        lookup_expr='in'
    )

    # Фильтр по студенту
    student_id = filters.NumberFilter(field_name='student_id')

    # Диапазон дат создания
    from_date = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    to_date = filters.DateFilter(field_name='created_at', lookup_expr='lte')

    # Диапазон сроков оплаты
    due_date_from = filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_date_to = filters.DateFilter(field_name='due_date', lookup_expr='lte')

    # Только просроченные счета
    overdue_only = filters.BooleanFilter(method='filter_overdue_only')

    # Только неоплаченные счета
    unpaid_only = filters.BooleanFilter(method='filter_unpaid_only')

    class Meta:
        model = Invoice
        fields = [
            'status', 'student_id', 'from_date', 'to_date',
            'due_date_from', 'due_date_to', 'overdue_only', 'unpaid_only'
        ]

    def filter_overdue_only(self, queryset, name, value):
        """Фильтрация просроченных счетов"""
        if value:
            today = timezone.now().date()
            return queryset.filter(
                due_date__lt=today,
                status__in=[
                    Invoice.Status.SENT,
                    Invoice.Status.VIEWED,
                    Invoice.Status.OVERDUE
                ]
            )
        return queryset

    def filter_unpaid_only(self, queryset, name, value):
        """Фильтрация неоплаченных счетов"""
        if value:
            return queryset.filter(
                status__in=[
                    Invoice.Status.DRAFT,
                    Invoice.Status.SENT,
                    Invoice.Status.VIEWED,
                    Invoice.Status.OVERDUE
                ]
            )
        return queryset


class TutorInvoiceFilter(InvoiceFilter):
    """
    Фильтр для счетов тьютора.
    Расширяет базовый InvoiceFilter дополнительными полями.
    """

    # Можно добавить дополнительные поля специфичные для тьютора
    # Например, фильтр по зачислению (enrollment)
    enrollment_id = filters.NumberFilter(field_name='enrollment_id')


class ParentInvoiceFilter(InvoiceFilter):
    """
    Фильтр для счетов родителя.
    Использует базовый InvoiceFilter с переименованием student_id в child_id.
    """

    # Переименовываем student_id в child_id для удобства родителей
    child_id = filters.NumberFilter(field_name='student_id')

    class Meta(InvoiceFilter.Meta):
        fields = [
            'status', 'child_id', 'from_date', 'to_date',
            'due_date_from', 'due_date_to', 'overdue_only', 'unpaid_only'
        ]
