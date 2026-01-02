"""
Service for admin schedule management.
Provides access to all lessons across all teachers.
"""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from django.db.models import Q, QuerySet
from django.contrib.auth import get_user_model
from django.utils import timezone

from scheduling.models import Lesson
from scheduling.serializers import LessonSerializer

User = get_user_model()

# Допустимые статусы уроков из модели Lesson
VALID_STATUSES = set(Lesson.Status.values)


class AdminScheduleService:
    """Service for admin schedule operations."""

    @staticmethod
    def get_all_lessons(
        teacher_id: Optional[int] = None,
        subject_id: Optional[int] = None,
        student_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[str] = None
    ) -> QuerySet:
        """
        Get all lessons with optional filtering.

        Args:
            teacher_id: Filter by teacher ID
            subject_id: Filter by subject ID
            student_id: Filter by student ID
            date_from: Start date filter
            date_to: End date filter
            status: Status filter (pending, confirmed, completed, cancelled)

        Returns:
            Filtered queryset of lessons
        """
        # Start with all lessons, optimize queries
        queryset = Lesson.objects.select_related(
            'teacher',
            'student',
            'subject'
        ).order_by('date', 'start_time')

        # Apply filters
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)

        if student_id:
            queryset = queryset.filter(student_id=student_id)

        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        if status:
            # Валидация статуса против допустимых значений из Lesson.STATUS_CHOICES
            if status in VALID_STATUSES:
                queryset = queryset.filter(status=status)
            # Если статус невалидный, игнорируем фильтр (возвращаем все)

        return queryset

    @staticmethod
    def get_schedule_stats() -> Dict[str, Any]:
        """
        Get statistics for admin dashboard.

        Returns:
            Dictionary with schedule statistics including:
            - total_lessons: общее количество уроков
            - today_lessons: уроки сегодня
            - week_ahead_lessons: уроки на следующую неделю (НЕ включая сегодня)
            - week_ago_lessons: уроки за прошлую неделю (для статистики)
            - pending_lessons: уроки в ожидании
            - completed_lessons: завершенные уроки
            - cancelled_lessons: отмененные уроки
        """
        # Используем timezone-aware дату для корректного сравнения
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        week_ahead = today + timedelta(days=7)

        return {
            'total_lessons': Lesson.objects.count(),
            'today_lessons': Lesson.objects.filter(date=today).count(),
            # week_ahead_lessons НЕ включает сегодня (date__gt вместо date__gte)
            'week_ahead_lessons': Lesson.objects.filter(
                date__gt=today,
                date__lte=week_ahead
            ).count(),
            # Используем week_ago для статистики прошедшей недели
            'week_ago_lessons': Lesson.objects.filter(
                date__gte=week_ago,
                date__lt=today
            ).count(),
            'pending_lessons': Lesson.objects.filter(status='pending').count(),
            'completed_lessons': Lesson.objects.filter(status='completed').count(),
            'cancelled_lessons': Lesson.objects.filter(status='cancelled').count(),
        }

    @staticmethod
    def get_teachers_list() -> List[Dict[str, Any]]:
        """
        Get list of all teachers for filtering.

        Returns:
            List of teacher data with id and name
        """
        teachers = User.objects.filter(role='teacher').values('id', 'first_name', 'last_name', 'email')
        return [
            {
                'id': t['id'],
                'name': f"{t['first_name']} {t['last_name']}".strip() or t['email']
            }
            for t in teachers
        ]

    @staticmethod
    def get_subjects_list() -> List[Dict[str, Any]]:
        """
        Get list of all subjects for filtering.

        Returns:
            List of subject data with id and name
        """
        from materials.models import Subject

        subjects = Subject.objects.all().values('id', 'name')
        return list(subjects)

    @staticmethod
    def get_students_list() -> List[Dict[str, Any]]:
        """
        Get list of all students for filtering.

        Returns:
            List of student data with id and name
        """
        students = User.objects.filter(role='student').values('id', 'first_name', 'last_name', 'email')
        return [
            {
                'id': s['id'],
                'name': f"{s['first_name']} {s['last_name']}".strip() or s['email']
            }
            for s in students
        ]