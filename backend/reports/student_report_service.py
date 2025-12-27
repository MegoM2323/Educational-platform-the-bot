from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Avg, Count, Sum, F, Max, Min
from django.utils import timezone
from django.core.cache import cache

from materials.models import SubjectEnrollment, Material, MaterialProgress
from assignments.models import Assignment, AssignmentSubmission
from knowledge_graph.models import LessonProgress, Element
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
    сводных данных прогресса за период с поддержкой:
    - Прогресса по предметам
    - Результатов заданий
    - Аналитики обучения
    - Отслеживания времени
    """

    CACHE_TTL = 3600  # 1 hour cache for progress data

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
    def get_student_progress_data(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Получение детальных данных прогресса студента за период.

        Включает: материалы, задания, аналитику, время обучения.
        """
        # Check cache
        cache_key = f"student_progress:{student.id}:{period_start}:{period_end}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        # Collect all progress data
        progress_data = {
            'student_id': student.id,
            'student_name': student.get_full_name(),
            'student_email': student.email,
            'period_start': str(period_start),
            'period_end': str(period_end),
            'materials': StudentReportService._get_material_progress(student, period_start, period_end),
            'assignments': StudentReportService._get_assignment_progress(student, period_start, period_end),
            'learning_analytics': StudentReportService._get_learning_analytics(student, period_start, period_end),
            'time_tracking': StudentReportService._get_time_tracking(student, period_start, period_end),
            'trends': StudentReportService._calculate_trends(student, period_start, period_end),
            'summary': StudentReportService._calculate_summary(student, period_start, period_end),
        }

        # Cache the result
        cache.set(cache_key, progress_data, StudentReportService.CACHE_TTL)

        return progress_data

    @staticmethod
    def _get_material_progress(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Получение прогресса по материалам по предметам."""
        material_progress = MaterialProgress.objects.filter(
            student=student,
            last_accessed__date__range=[period_start, period_end]
        ).select_related('material__subject')

        # Group by subject
        subjects_data = {}
        total_materials = 0
        completed_count = 0

        for mp in material_progress:
            subject = mp.material.subject
            subject_id = subject.id if subject else 'unknown'
            subject_name = subject.name if subject else 'Неизвестный предмет'

            if subject_id not in subjects_data:
                subjects_data[subject_id] = {
                    'name': subject_name,
                    'materials': [],
                    'total': 0,
                    'completed': 0,
                    'completion_percentage': 0,
                    'average_progress': 0
                }

            subjects_data[subject_id]['materials'].append({
                'material_id': mp.material.id,
                'title': mp.material.title,
                'progress_percentage': mp.progress_percentage,
                'is_completed': mp.is_completed,
                'time_spent_minutes': mp.time_spent or 0,
                'last_accessed': mp.last_accessed.isoformat() if mp.last_accessed else None,
            })

            total_materials += 1
            if mp.is_completed:
                completed_count += 1

        # Calculate subject-level metrics
        for subject_id, subject_data in subjects_data.items():
            materials = subject_data['materials']
            subject_data['total'] = len(materials)
            subject_data['completed'] = sum(1 for m in materials if m['is_completed'])
            subject_data['completion_percentage'] = (
                (subject_data['completed'] / subject_data['total'] * 100)
                if subject_data['total'] > 0 else 0
            )
            subject_data['average_progress'] = (
                sum(m['progress_percentage'] for m in materials) / len(materials)
                if materials else 0
            )

        return {
            'by_subject': subjects_data,
            'total_materials': total_materials,
            'completed_materials': completed_count,
            'overall_completion_percentage': (
                (completed_count / total_materials * 100)
                if total_materials > 0 else 0
            )
        }

    @staticmethod
    def _get_assignment_progress(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Получение результатов по заданиям."""
        submissions = AssignmentSubmission.objects.filter(
            student=student,
            submitted_at__date__range=[period_start, period_end]
        ).select_related('assignment')

        assignment_data = []
        total_assignments = 0
        completed_assignments = 0
        scores = []

        for submission in submissions:
            total_assignments += 1
            if submission.is_graded:
                completed_assignments += 1

            score = submission.score if submission.score is not None else 0
            scores.append(float(score))

            assignment_data.append({
                'assignment_id': submission.assignment.id,
                'title': submission.assignment.title,
                'score': score,
                'max_score': submission.assignment.max_score or 100,
                'percentage': (score / (submission.assignment.max_score or 100) * 100) if submission.assignment.max_score else 0,
                'is_graded': submission.is_graded,
                'submitted_at': submission.submitted_at.isoformat() if submission.submitted_at else None,
                'feedback': submission.feedback or '',
            })

        average_score = sum(scores) / len(scores) if scores else 0

        return {
            'assignments': assignment_data,
            'total_assignments': total_assignments,
            'completed_assignments': completed_assignments,
            'completion_percentage': (
                (completed_assignments / total_assignments * 100)
                if total_assignments > 0 else 0
            ),
            'average_score': round(average_score, 2),
            'highest_score': max(scores) if scores else 0,
            'lowest_score': min(scores) if scores else 0,
        }

    @staticmethod
    def _get_learning_analytics(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Получение аналитики обучения."""
        # Knowledge graph progress
        kg_progress = LessonProgress.objects.filter(
            student=student,
            updated_at__date__range=[period_start, period_end]
        ).select_related('element__lesson')

        total_lessons = 0
        completed_lessons = 0
        lesson_data = []

        for progress in kg_progress:
            total_lessons += 1
            if progress.is_completed:
                completed_lessons += 1

            lesson_data.append({
                'lesson_id': progress.element.lesson.id if progress.element.lesson else None,
                'element_id': progress.element.id,
                'title': progress.element.name,
                'is_completed': progress.is_completed,
                'completion_percentage': progress.completion_percentage or 0,
                'updated_at': progress.updated_at.isoformat(),
            })

        # Calculate engagement metrics
        activity_days = MaterialProgress.objects.filter(
            student=student,
            last_accessed__date__range=[period_start, period_end]
        ).values('last_accessed__date').distinct().count()

        return {
            'lessons': lesson_data,
            'total_lessons': total_lessons,
            'completed_lessons': completed_lessons,
            'completion_percentage': (
                (completed_lessons / total_lessons * 100)
                if total_lessons > 0 else 0
            ),
            'engagement_days': activity_days,
            'engagement_percentage': (
                (activity_days / ((period_end - period_start).days + 1) * 100)
                if (period_end - period_start).days > 0 else 0
            ),
        }

    @staticmethod
    def _get_time_tracking(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Получение данных отслеживания времени."""
        material_progress = MaterialProgress.objects.filter(
            student=student,
            last_accessed__date__range=[period_start, period_end]
        )

        total_time_minutes = 0
        time_by_subject = {}

        for mp in material_progress:
            time_spent = mp.time_spent or 0
            total_time_minutes += time_spent

            subject = mp.material.subject
            subject_name = subject.name if subject else 'Неизвестный предмет'

            if subject_name not in time_by_subject:
                time_by_subject[subject_name] = 0
            time_by_subject[subject_name] += time_spent

        # Calculate daily average
        total_days = (period_end - period_start).days + 1
        daily_average = total_time_minutes / total_days if total_days > 0 else 0

        return {
            'total_time_minutes': total_time_minutes,
            'total_time_hours': round(total_time_minutes / 60, 2),
            'daily_average_minutes': round(daily_average, 2),
            'by_subject': time_by_subject,
        }

    @staticmethod
    def _calculate_trends(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Расчёт тенденций улучшения/снижения производительности."""
        # Split period into two halves
        mid_date = period_start + (period_end - period_start) / 2

        # First half stats
        first_half_submissions = AssignmentSubmission.objects.filter(
            student=student,
            submitted_at__date__range=[period_start, mid_date]
        )
        first_half_scores = [
            float(s.score) for s in first_half_submissions
            if s.score is not None
        ]
        first_half_avg = sum(first_half_scores) / len(first_half_scores) if first_half_scores else 0

        # Second half stats
        second_half_submissions = AssignmentSubmission.objects.filter(
            student=student,
            submitted_at__date__range=[mid_date, period_end]
        )
        second_half_scores = [
            float(s.score) for s in second_half_submissions
            if s.score is not None
        ]
        second_half_avg = sum(second_half_scores) / len(second_half_scores) if second_half_scores else 0

        # Determine trend
        trend_direction = 'stable'
        trend_value = 0
        if second_half_avg > first_half_avg * 1.05:  # 5% improvement threshold
            trend_direction = 'improving'
            trend_value = round(second_half_avg - first_half_avg, 2)
        elif second_half_avg < first_half_avg * 0.95:  # 5% decline threshold
            trend_direction = 'declining'
            trend_value = round(second_half_avg - first_half_avg, 2)

        return {
            'direction': trend_direction,
            'value': trend_value,
            'first_half_average': round(first_half_avg, 2),
            'second_half_average': round(second_half_avg, 2),
            'interpretation': StudentReportService._get_trend_interpretation(trend_direction, trend_value),
        }

    @staticmethod
    def _calculate_summary(
        student: User,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Расчёт сводной статистики."""
        all_data = {
            'materials': StudentReportService._get_material_progress(student, period_start, period_end),
            'assignments': StudentReportService._get_assignment_progress(student, period_start, period_end),
            'learning_analytics': StudentReportService._get_learning_analytics(student, period_start, period_end),
        }

        material_completion = all_data['materials']['overall_completion_percentage']
        assignment_avg = all_data['assignments']['average_score']
        lesson_completion = all_data['learning_analytics']['completion_percentage']

        # Calculate overall progress percentage
        overall_progress = (
            (material_completion + lesson_completion) / 2
            if (material_completion or lesson_completion) else 0
        )

        # Determine overall grade based on assignment average
        overall_grade = StudentReportService._calculate_grade(assignment_avg)

        # Get class average for comparison
        class_average = StudentReportService._get_class_average(student, period_start, period_end)
        score_vs_class = StudentReportService._calculate_score_comparison(assignment_avg, class_average)

        return {
            'overall_progress_percentage': round(overall_progress, 2),
            'overall_grade': overall_grade,
            'overall_score': round(assignment_avg, 2),
            'total_study_hours': round(
                all_data.get('time_tracking', {}).get('total_time_hours', 0), 2
            ),
            'performance_summary': StudentReportService._get_performance_summary(
                material_completion,
                assignment_avg,
                lesson_completion
            ),
            'class_comparison': {
                'class_average': round(class_average, 2),
                'student_vs_class': score_vs_class,
            },
        }

    @staticmethod
    def _get_trend_interpretation(direction: str, value: float) -> str:
        """Получение текстовой интерпретации тенденции."""
        if direction == 'improving':
            return f"Производительность улучшается на {abs(value):.1f} пункта в среднем"
        elif direction == 'declining':
            return f"Производительность снижается на {abs(value):.1f} пункта в среднем"
        else:
            return "Производительность остаётся стабильной"

    @staticmethod
    def _calculate_grade(score: float) -> str:
        """Расчёт общей оценки на основе среднего балла."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    @staticmethod
    def _get_performance_summary(
        material_completion: float,
        assignment_avg: float,
        lesson_completion: float
    ) -> str:
        """Получение текстовой сводки производительности."""
        if material_completion > 75 and assignment_avg > 80 and lesson_completion > 75:
            return "Отличная производительность - студент показывает высокий уровень освоения материала"
        elif material_completion > 50 and assignment_avg > 70 and lesson_completion > 50:
            return "Хорошая производительность - студент демонстрирует понимание материала"
        elif material_completion > 25 or assignment_avg > 50 or lesson_completion > 25:
            return "Удовлетворительная производительность - требуется дополнительная поддержка"
        else:
            return "Низкая производительность - рекомендуется немедленное вмешательство"

    @staticmethod
    def _get_class_average(
        student: User,
        period_start: date,
        period_end: date
    ) -> float:
        """Получение среднего балла студентов класса за период.

        Определяет класс студента по зачислениям и вычисляет среднее
        по всем студентам в этом классе.
        """
        # Get student's classes via SubjectEnrollment
        student_subjects = SubjectEnrollment.objects.filter(
            student=student
        ).values_list('subject_id', flat=True).distinct()

        if not student_subjects:
            return 0.0

        # Get all students in same subjects
        class_students = User.objects.filter(
            role='student',
            subject_enrollment__subject_id__in=student_subjects
        ).distinct()

        if not class_students:
            return 0.0

        # Get average score for all students in class during period
        submissions = AssignmentSubmission.objects.filter(
            student__in=class_students,
            submitted_at__date__range=[period_start, period_end]
        )

        scores = [float(s.score) for s in submissions if s.score is not None]

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    @staticmethod
    def _calculate_score_comparison(student_score: float, class_average: float) -> Dict[str, Any]:
        """Расчёт сравнения баллов студента с классом.

        Returns:
            Dict with comparison metrics and interpretation
        """
        if class_average == 0:
            return {
                'difference': 0,
                'percentage_difference': 0,
                'position': 'no_data',
                'interpretation': 'Недостаточно данных для сравнения'
            }

        difference = student_score - class_average
        percentage_diff = (difference / class_average * 100) if class_average > 0 else 0

        # Determine position relative to class average (threshold: 2 points)
        if difference >= 2:
            position = 'above_average'
            interpretation = f"Выше среднего по классу на {abs(difference):.1f} пункта"
        elif difference <= -2:
            position = 'below_average'
            interpretation = f"Ниже среднего по классу на {abs(difference):.1f} пункта"
        else:
            position = 'at_average'
            interpretation = "На уровне среднего по классу"

        return {
            'difference': round(difference, 2),
            'percentage_difference': round(percentage_diff, 2),
            'position': position,
            'interpretation': interpretation,
        }


