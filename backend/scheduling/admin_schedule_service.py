"""
Service for admin schedule management.
Provides access to all lessons across all teachers.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from django.db.models import Q, QuerySet
from django.contrib.auth import get_user_model

from scheduling.models import Lesson
from scheduling.serializers import LessonSerializer

User = get_user_model()


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
            queryset = queryset.filter(status=status)

        return queryset

    @staticmethod
    def get_schedule_stats() -> Dict[str, Any]:
        """
        Get statistics for admin dashboard.

        Returns:
            Dictionary with schedule statistics
        """
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        week_ahead = today + timedelta(days=7)

        return {
            'total_lessons': Lesson.objects.count(),
            'today_lessons': Lesson.objects.filter(date=today).count(),
            'week_ahead_lessons': Lesson.objects.filter(
                date__gte=today,
                date__lte=week_ahead
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