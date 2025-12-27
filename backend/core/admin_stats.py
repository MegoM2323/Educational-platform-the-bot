"""
Сервисные функции для статистики админ-панели.

Содержит оптимизированные запросы для получения различных метрик
по пользователям, урокам, счетам и графам знаний.
"""

from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from accounts.models import User, StudentProfile
from scheduling.models import Lesson
from invoices.models import Invoice
from knowledge_graph.models import Lesson as KGLesson, Element, LessonProgress


def get_dashboard_stats():
    """
    Главная статистика для админ-панели.

    Returns:
        dict: Статистика по пользователям, активности и производительности
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start.replace(day=1)

    # Статистика пользователей (одним запросом)
    user_stats = User.objects.aggregate(
        total=Count('id'),
        students=Count('id', filter=Q(role='student')),
        teachers=Count('id', filter=Q(role='teacher')),
        tutors=Count('id', filter=Q(role='tutor')),
        parents=Count('id', filter=Q(role='parent'))
    )

    # Активность (оптимизировано)
    active_today = User.objects.filter(
        last_login__gte=today_start
    ).count()

    lessons_today = Lesson.objects.filter(
        date=now.date()
    ).count()

    invoices_unpaid = Invoice.objects.filter(
        status__in=['sent', 'viewed', 'overdue']
    ).count()

    # Производительность
    # Средний прогресс студентов
    avg_progress = StudentProfile.objects.aggregate(
        avg=Avg('progress_percentage')
    )['avg'] or 0.0

    # Уроки за неделю (completed)
    lessons_completed_week = Lesson.objects.filter(
        status='completed',
        updated_at__gte=week_start
    ).count()

    # Выручка за месяц (оплаченные счета)
    revenue_month = Invoice.objects.filter(
        status='paid',
        paid_at__gte=month_start
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    return {
        'users': {
            'total': user_stats['total'],
            'students': user_stats['students'],
            'teachers': user_stats['teachers'],
            'tutors': user_stats['tutors'],
            'parents': user_stats['parents']
        },
        'activity': {
            'online_now': 0,  # Требует Redis или отдельной логики для WebSocket
            'active_today': active_today,
            'lessons_today': lessons_today,
            'invoices_unpaid': invoices_unpaid
        },
        'performance': {
            'avg_student_progress': round(avg_progress, 1),
            'lessons_completed_this_week': lessons_completed_week,
            'revenue_this_month': float(revenue_month)
        }
    }


def get_user_stats(role=None):
    """
    Статистика по пользователям с фильтрацией по роли.

    Args:
        role (str, optional): Роль для фильтрации (student, teacher, tutor, parent)

    Returns:
        dict: Подробная статистика по пользователям
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Базовая фильтрация
    queryset = User.objects.all()
    if role:
        queryset = queryset.filter(role=role)

    # Общая статистика
    total = queryset.count()
    active = queryset.filter(is_active=True).count()
    inactive = total - active

    # Создано сегодня/неделю
    created_today = queryset.filter(created_at__gte=today_start).count()
    created_week = queryset.filter(created_at__gte=week_start).count()

    result = {
        'role': role or 'all',
        'total': total,
        'active': active,
        'inactive': inactive,
        'created_today': created_today,
        'created_this_week': created_week
    }

    # Дополнительная статистика для студентов (по классам)
    if role == 'student':
        # Группировка по классам
        grades = StudentProfile.objects.values('grade').annotate(
            count=Count('id')
        ).order_by('grade')

        by_grade = {
            grade['grade'] or 'Не указан': grade['count']
            for grade in grades
        }

        result['by_grade'] = by_grade

    return result


def get_lesson_stats():
    """
    Статистика по урокам (scheduling.Lesson).

    Returns:
        dict: Статистика по количеству уроков и их статусам
    """
    now = timezone.now()
    today = now.date()
    week_start = today - timedelta(days=7)

    # Общее количество уроков
    total_lessons = Lesson.objects.count()

    # Уроки сегодня
    lessons_today = Lesson.objects.filter(date=today).count()

    # Уроки за неделю
    lessons_week = Lesson.objects.filter(
        date__gte=week_start,
        date__lte=today
    ).count()

    # По статусам
    status_stats = Lesson.objects.values('status').annotate(
        count=Count('id')
    )

    by_status = {
        stat['status']: stat['count']
        for stat in status_stats
    }

    # Средняя длительность урока (в минутах)
    # Вычисляем как разницу между start_time и end_time
    lessons_with_times = Lesson.objects.exclude(
        start_time__isnull=True
    ).exclude(
        end_time__isnull=True
    )

    total_duration = 0
    count = 0
    for lesson in lessons_with_times[:1000]:  # Ограничение для производительности
        # Конвертируем time в datetime для вычисления разницы
        start = timezone.datetime.combine(timezone.now().date(), lesson.start_time)
        end = timezone.datetime.combine(timezone.now().date(), lesson.end_time)
        duration = (end - start).total_seconds() / 60
        total_duration += duration
        count += 1

    avg_duration = round(total_duration / count) if count > 0 else 0

    return {
        'total_lessons': total_lessons,
        'lessons_today': lessons_today,
        'lessons_this_week': lessons_week,
        'by_status': by_status,
        'avg_duration_minutes': avg_duration
    }


def get_invoice_stats():
    """
    Статистика по счетам (invoices.Invoice).

    Returns:
        dict: Статистика по количеству счетов и финансам
    """
    # Общее количество счетов
    total_invoices = Invoice.objects.count()

    # По статусам
    unpaid = Invoice.objects.filter(
        status__in=['sent', 'viewed', 'overdue']
    ).count()

    paid = Invoice.objects.filter(status='paid').count()

    # Финансовая статистика
    financial_stats = Invoice.objects.aggregate(
        total_revenue=Sum('amount'),
        paid_revenue=Sum('amount', filter=Q(status='paid')),
        unpaid_amount=Sum('amount', filter=Q(status__in=['sent', 'viewed', 'overdue']))
    )

    total_revenue = float(financial_stats['total_revenue'] or Decimal('0.00'))
    paid_revenue = float(financial_stats['paid_revenue'] or Decimal('0.00'))
    unpaid_amount = float(financial_stats['unpaid_amount'] or Decimal('0.00'))

    # Средняя сумма счета
    avg_invoice = total_revenue / total_invoices if total_invoices > 0 else 0

    # Просроченные счета
    overdue_count = Invoice.objects.filter(status='overdue').count()

    return {
        'total_invoices': total_invoices,
        'unpaid': unpaid,
        'paid': paid,
        'total_revenue': total_revenue,
        'paid_revenue': paid_revenue,
        'unpaid_amount': unpaid_amount,
        'avg_invoice_amount': round(avg_invoice, 2),
        'overdue_count': overdue_count
    }


def get_knowledge_graph_stats():
    """
    Статистика по графу знаний (knowledge_graph.Lesson, Element).

    Returns:
        dict: Статистика по урокам и элементам графа знаний
    """
    # Общее количество уроков в банке
    total_lessons = KGLesson.objects.count()

    # Общее количество элементов
    total_elements = Element.objects.count()

    # Количество студентов с прогрессом
    students_with_progress = LessonProgress.objects.values('student').distinct().count()

    # Средний процент завершения
    avg_completion = LessonProgress.objects.aggregate(
        avg=Avg('completion_percent')
    )['avg'] or 0.0

    # Самый сложный урок (у которого самый низкий средний процент завершения)
    lessons_completion = LessonProgress.objects.values(
        'graph_lesson__lesson__title'
    ).annotate(
        avg_completion=Avg('completion_percent'),
        count=Count('id')
    ).filter(
        count__gte=3  # Минимум 3 попытки для репрезентативности
    ).order_by('avg_completion')

    most_difficult = None
    if lessons_completion.exists():
        most_difficult = lessons_completion.first()['graph_lesson__lesson__title']

    return {
        'total_lessons': total_lessons,
        'total_elements': total_elements,
        'students_with_progress': students_with_progress,
        'avg_completion_rate': round(avg_completion, 1),
        'most_difficult_lesson': most_difficult or 'Недостаточно данных'
    }
