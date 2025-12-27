from django.db.models import Q, Count, Avg, Sum, Prefetch
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .models import Material, MaterialProgress, Subject, SubjectEnrollment
from chat.models import ChatRoom, Message
from reports.models import StudentReport, Report
from .cache_utils import cache_dashboard_data, cache_material_data, DashboardCacheManager

User = get_user_model()


class TutorDashboardService:
    """
    Сервис для работы с дашбордом тьютора
    Обеспечивает управление студентами, назначение предметов и отчетность
    """

    def __init__(self, tutor: User, request=None):
        """
        Инициализация сервиса для конкретного тьютора

        Args:
            tutor: Пользователь с ролью 'tutor'
            request: HTTP request для формирования абсолютных URL (опционально)
        """
        if tutor.role != User.Role.TUTOR:
            raise PermissionDenied("Только тьюторы могут использовать этот сервис")

        self.tutor = tutor
        self.request = request

    def _build_file_url(self, file_field):
        """Формирует абсолютный URL для файла"""
        if not file_field:
            return None
        if self.request:
            return self.request.build_absolute_uri(file_field.url)
        return file_field.url

    def get_students(self) -> List[Dict[str, Any]]:
        """
        Получить список студентов тьютора

        Returns:
            Список словарей с информацией о студентах
        """
        # Оптимизированный queryset для активных enrollments
        active_enrollments = SubjectEnrollment.objects.filter(
            is_active=True
        ).select_related('subject', 'teacher')

        # Получаем студентов тьютора через StudentProfile
        students = User.objects.filter(
            role=User.Role.STUDENT,
            student_profile__tutor=self.tutor,
            is_active=True
        ).select_related(
            'student_profile',
            'student_profile__parent'  # Избегаем N+1 для родителей
        ).prefetch_related(
            Prefetch('subject_enrollments', queryset=active_enrollments, to_attr='active_enrollments'),
            'assigned_materials'
        ).distinct()

        result = []
        for student in students:
            # Получаем профиль студента
            try:
                profile = student.student_profile
                profile_data = {
                    'grade': profile.grade,
                    'goal': profile.goal,
                    'progress_percentage': profile.progress_percentage,
                    'streak_days': profile.streak_days,
                    'total_points': profile.total_points,
                    'accuracy_percentage': profile.accuracy_percentage
                }
            except Exception:
                profile_data = {
                    'grade': 'Не указан',
                    'goal': '',
                    'progress_percentage': 0,
                    'streak_days': 0,
                    'total_points': 0,
                    'accuracy_percentage': 0
                }

            # Получаем предметы студента из prefetched данных
            # Используем active_enrollments (to_attr из Prefetch) вместо .filter()
            enrollments = student.active_enrollments if hasattr(student, 'active_enrollments') else []
            subjects = [
                {
                    'id': enrollment.subject.id,
                    'name': enrollment.get_subject_name(),
                    'teacher_name': enrollment.teacher.get_full_name(),
                    'enrollment_id': enrollment.id
                }
                for enrollment in enrollments
            ]

            # Получаем родителя студента
            parent = profile.parent if hasattr(student, 'student_profile') and hasattr(student.student_profile, 'parent') else None

            result.append({
                'id': student.id,
                'username': student.username,
                'full_name': student.get_full_name() or student.username,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email or '',
                'avatar': self._build_file_url(student.avatar) if student.avatar else None,
                'profile': profile_data,
                'subjects': subjects,
                'parent': {
                    'id': parent.id,
                    'name': parent.get_full_name(),
                    'email': parent.email
                } if parent else None
            })

        return result

    def get_student_subjects(self, student_id: int) -> List[Dict[str, Any]]:
        """
        Получить предметы конкретного студента

        Args:
            student_id: ID студента

        Returns:
            Список предметов студента
        """
        # Проверяем, что студент принадлежит тьютору
        try:
            student = User.objects.get(
                id=student_id,
                role=User.Role.STUDENT,
                student_profile__tutor=self.tutor
            )
        except User.DoesNotExist:
            raise PermissionDenied("Студент не найден или не принадлежит данному тьютору")

        enrollments = SubjectEnrollment.objects.filter(
            student=student,
            is_active=True
        ).select_related('subject', 'teacher')

        result = []
        for enrollment in enrollments:
            result.append({
                'id': enrollment.subject.id,
                'enrollment_id': enrollment.id,
                'name': enrollment.get_subject_name(),
                'description': enrollment.subject.description,
                'color': enrollment.subject.color,
                'teacher': {
                    'id': enrollment.teacher.id,
                    'name': enrollment.teacher.get_full_name(),
                    'email': enrollment.teacher.email
                },
                'enrolled_at': enrollment.enrolled_at,
                'custom_subject_name': enrollment.custom_subject_name
            })

        return result

    def get_student_progress(self, student_id: int) -> Dict[str, Any]:
        """
        Получить прогресс студента по всем предметам

        Args:
            student_id: ID студента

        Returns:
            Словарь со статистикой прогресса
        """
        # Проверяем, что студент принадлежит тьютору
        try:
            student = User.objects.get(
                id=student_id,
                role=User.Role.STUDENT,
                student_profile__tutor=self.tutor
            )
        except User.DoesNotExist:
            raise PermissionDenied("Студент не найден или не принадлежит данному тьютору")

        # Общая статистика прогресса
        progress_stats = MaterialProgress.objects.filter(
            student=student
        ).aggregate(
            total_materials=Count('id'),
            completed_materials=Count('id', filter=Q(is_completed=True)),
            avg_progress=Avg('progress_percentage'),
            total_time=Sum('time_spent')
        )

        total_materials = progress_stats['total_materials'] or 0
        completed_materials = progress_stats['completed_materials'] or 0
        avg_progress = progress_stats['avg_progress'] or 0
        total_time = progress_stats['total_time'] or 0

        # Прогресс по предметам - оптимизация N+1
        # Получаем все subject_id из enrollments
        enrollments = SubjectEnrollment.objects.filter(
            student=student,
            is_active=True
        ).select_related('subject', 'teacher')

        # Получаем статистику по всем предметам одним запросом
        subject_stats_data = MaterialProgress.objects.filter(
            student=student,
            material__subject__in=[e.subject for e in enrollments]
        ).values('material__subject__id', 'material__subject__name').annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(is_completed=True)),
            avg_progress=Avg('progress_percentage')
        )

        # Создаем словарь для быстрого поиска статистики по subject_id
        stats_by_subject = {
            item['material__subject__id']: item
            for item in subject_stats_data
        }

        subject_progress = []
        for enrollment in enrollments:
            subject_stats = stats_by_subject.get(enrollment.subject.id, {
                'total': 0,
                'completed': 0,
                'avg_progress': 0
            })

            subject_progress.append({
                'subject': enrollment.get_subject_name(),
                'subject_id': enrollment.subject.id,
                'teacher': enrollment.teacher.get_full_name(),
                'total_materials': subject_stats['total'] or 0,
                'completed_materials': subject_stats['completed'] or 0,
                'average_progress': round(subject_stats.get('avg_progress') or 0, 1)
            })

        return {
            'student': {
                'id': student.id,
                'name': student.get_full_name()
            },
            'total_materials': total_materials,
            'completed_materials': completed_materials,
            'completion_percentage': round((completed_materials / total_materials * 100) if total_materials > 0 else 0, 1),
            'average_progress': round(avg_progress, 1),
            'total_study_time': total_time,
            'subject_progress': subject_progress
        }

    def assign_subject(self, student_id: int, subject_id: int, teacher_id: int,
                      custom_subject_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Назначить предмет студенту с преподавателем

        Args:
            student_id: ID студента
            subject_id: ID предмета
            teacher_id: ID преподавателя
            custom_subject_name: Кастомное название предмета (опционально)

        Returns:
            Результат операции
        """
        try:
            # Проверяем, что студент принадлежит тьютору
            student = User.objects.get(
                id=student_id,
                role=User.Role.STUDENT,
                student_profile__tutor=self.tutor
            )
        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Студент не найден или не принадлежит данному тьютору'
            }

        try:
            subject = Subject.objects.get(id=subject_id)
            teacher = User.objects.get(id=teacher_id, role=User.Role.TEACHER)
        except Subject.DoesNotExist:
            return {
                'success': False,
                'message': 'Предмет не найден'
            }
        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Преподаватель не найден'
            }

        # Проверяем, не назначен ли уже этот предмет с этим преподавателем
        existing_enrollment = SubjectEnrollment.objects.filter(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        ).first()

        if existing_enrollment:
            return {
                'success': False,
                'message': 'Этот предмет с данным преподавателем уже назначен студенту'
            }

        # Создаем зачисление
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            assigned_by=self.tutor,
            custom_subject_name=custom_subject_name,
            is_active=True
        )

        return {
            'success': True,
            'message': f'Предмет "{subject.name}" успешно назначен студенту',
            'enrollment_id': enrollment.id,
            'subject_name': enrollment.get_subject_name()
        }

    def create_student_report(self, student_id: int, parent_id: int,
                             report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать отчет о студенте для родителя

        Args:
            student_id: ID студента
            parent_id: ID родителя
            report_data: Данные отчета

        Returns:
            Результат создания отчета
        """
        try:
            # Проверяем, что студент принадлежит тьютору
            student = User.objects.get(
                id=student_id,
                role=User.Role.STUDENT,
                student_profile__tutor=self.tutor
            )

            # Проверяем, что родитель является родителем студента
            parent = User.objects.get(
                id=parent_id,
                role=User.Role.PARENT
            )

            if not hasattr(student, 'student_profile') or student.student_profile.parent != parent:
                return {
                    'success': False,
                    'message': 'Указанный родитель не является родителем данного студента'
                }

        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Студент или родитель не найден'
            }

        try:
            from django.utils import timezone
            from datetime import timedelta

            # Определяем даты периода
            start_date = report_data.get('period_start')
            end_date = report_data.get('period_end')

            if isinstance(start_date, str):
                from datetime import datetime
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if isinstance(end_date, str):
                from datetime import datetime
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            if not start_date:
                start_date = timezone.now().date() - timedelta(days=7)
            if not end_date:
                end_date = timezone.now().date()

            # Создаем отчет
            report = Report.objects.create(
                title=report_data.get('title', f'Отчет по студенту {student.get_full_name()}'),
                description=report_data.get('description', ''),
                type=Report.Type.CUSTOM,
                status=Report.Status.DRAFT,
                author=self.tutor,
                start_date=start_date,
                end_date=end_date,
                content={
                    'student_id': student.id,
                    'student_name': student.get_full_name(),
                    'report_content': report_data.get('content', ''),
                    'progress_data': report_data.get('progress_data', {})
                }
            )

            # Создаем получателя отчета
            from reports.models import ReportRecipient
            ReportRecipient.objects.create(
                report=report,
                recipient=parent
            )

            return {
                'success': True,
                'message': 'Отчет успешно создан и отправлен родителю',
                'report_id': report.id
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при создании отчета: {str(e)}'
            }

    def get_tutor_reports(self) -> List[Dict[str, Any]]:
        """
        Получить отчеты тьютора

        Returns:
            Список отчетов
        """
        # Оптимизация: prefetch recipients с select_related для recipient user
        from django.db.models import Prefetch
        from reports.models import ReportRecipient

        reports = Report.objects.filter(
            author=self.tutor
        ).prefetch_related(
            Prefetch(
                'recipients',
                queryset=ReportRecipient.objects.select_related('recipient'),
                to_attr='prefetched_recipients'
            )
        ).order_by('-created_at')

        result = []
        for report in reports:
            # Получаем получателей из prefetched данных
            recipients_data = []
            for recipient_rel in report.prefetched_recipients:
                # Проверяем наличие атрибута is_read (может не быть в старых записях)
                is_read = getattr(recipient_rel, 'is_read', hasattr(recipient_rel, 'read_at') and recipient_rel.read_at is not None)
                recipients_data.append({
                    'id': recipient_rel.recipient.id,
                    'name': recipient_rel.recipient.get_full_name(),
                    'email': recipient_rel.recipient.email,
                    'is_read': is_read,
                    'read_at': recipient_rel.read_at
                })

            result.append({
                'id': report.id,
                'title': report.title,
                'description': report.description,
                'content': report.content,
                'type': report.type,
                'status': report.status,
                'start_date': report.start_date,
                'end_date': report.end_date,
                'created_at': report.created_at,
                'recipients': recipients_data
            })

        return result

    @cache_dashboard_data(timeout=300)  # 5 минут
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Получить полные данные для дашборда тьютора

        Returns:
            Словарь со всеми данными дашборда
        """
        students = self.get_students()

        # Подсчет статистики
        total_students = len(students)

        # Общий прогресс всех студентов
        total_progress = 0
        if students:
            total_progress = sum(s['profile']['progress_percentage'] for s in students) / total_students

        # Всего предметов назначено
        total_subjects_assigned = SubjectEnrollment.objects.filter(
            student__student_profile__tutor=self.tutor,
            is_active=True
        ).count()

        return {
            'tutor_info': {
                'id': self.tutor.id,
                'name': self.tutor.get_full_name(),
                'username': self.tutor.username,
                'role': self.tutor.role,
                'avatar': self._build_file_url(self.tutor.avatar) if self.tutor.avatar else None
            },
            'statistics': {
                'total_students': total_students,
                'average_progress': round(total_progress, 1),
                'total_subjects_assigned': total_subjects_assigned
            },
            'students': students,
            'reports': self.get_tutor_reports()[:3]  # Последние 3 отчета
        }
