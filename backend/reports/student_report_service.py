from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from materials.models import SubjectEnrollment
from .models import StudentReport


User = get_user_model()


@dataclass
class CreateStudentReportInput:
    teacher: User
    student: User
    title: str
    period_start: str
    period_end: str
    content: Dict[str, Any]
    description: str = ""
    report_type: str = StudentReport.ReportType.PROGRESS
    overall_grade: str = ""
    progress_percentage: int = 0
    attendance_percentage: int = 0
    behavior_rating: int = 5
    recommendations: str = ""
    concerns: str = ""
    achievements: str = ""


class StudentReportService:
    """Сервис работы с персональными отчётами студентов.

    Предоставляет создание отчёта, выборку студентов преподавателя и получение
    сводных данных прогресса за период (упрощённая версия по требованиям).
    """

    @staticmethod
    def get_teacher_students(teacher: User) -> List[Dict[str, Any]]:
        """Возвращает уникальный список студентов, у которых есть активные зачисления у преподавателя.
        """
        enrollments = (
            SubjectEnrollment.objects
            .filter(teacher=teacher, is_active=True)
            .select_related('student')
        )

        seen_ids = set()
        students: List[Dict[str, Any]] = []
        for e in enrollments:
            if e.student_id in seen_ids:
                continue
            seen_ids.add(e.student_id)
            students.append({
                'id': e.student.id,
                'first_name': e.student.first_name,
                'last_name': e.student.last_name,
                'email': e.student.email,
            })
        return students

    @staticmethod
    @transaction.atomic
    def create_student_report(data: CreateStudentReportInput) -> StudentReport:
        """Создание персонального отчёта преподавателем.

        Валидирует базовые права: студент должен быть среди студентов преподавателя.
        """
        # Валидация принадлежности студента преподавателю
        is_student_of_teacher = SubjectEnrollment.objects.filter(
            teacher=data.teacher,
            student=data.student,
            is_active=True,
        ).exists()

        if not is_student_of_teacher:
            raise ValueError('Студент не закреплён за данным преподавателем')

        report = StudentReport.objects.create(
            title=data.title,
            description=data.description,
            report_type=data.report_type,
            status=StudentReport.Status.DRAFT,
            teacher=data.teacher,
            student=data.student,
            period_start=data.period_start,
            period_end=data.period_end,
            content=data.content or {},
            overall_grade=data.overall_grade,
            progress_percentage=data.progress_percentage,
            attendance_percentage=data.attendance_percentage,
            behavior_rating=data.behavior_rating,
            recommendations=data.recommendations,
            concerns=data.concerns,
            achievements=data.achievements,
        )
        return report

    @staticmethod
    def get_student_progress_data(student: User, period_start, period_end) -> Dict[str, Any]:
        """Упрощённый расчёт прогресса за период.

        В проде можно агрегировать из AnalyticsData/MaterialProgress. Здесь —
        возвращаем базовую структуру согласно требованиям, без тяжёлых запросов.
        """
        return {
            'student_id': student.id,
            'student_name': student.get_full_name(),
            'period_start': str(period_start),
            'period_end': str(period_end),
            'progress_percentage': 0,
            'average_score': 0.0,
            'materials_studied': 0,
            'completed_assignments': 0,
            'total_assignments': 0,
            'streak_days': getattr(getattr(student, 'student_profile', None), 'streak_days', 0),
            'last_activity': timezone.now().isoformat(),
        }


