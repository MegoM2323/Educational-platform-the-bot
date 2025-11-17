from django.db.models import Q, Count, Avg, Sum, F, Prefetch
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .models import Material, MaterialProgress, Subject, SubjectEnrollment
from chat.models import ChatRoom, Message
from reports.models import StudentReport, Report, ReportRecipient, AnalyticsData
from .cache_utils import cache_dashboard_data, cache_material_data, DashboardCacheManager

User = get_user_model()


class TeacherDashboardService:
    """
    Сервис для работы с дашбордом преподавателя
    Обеспечивает распределение материалов, отчетность и доступ к общему чату
    """
    
    def __init__(self, teacher: User, request=None):
        """
        Инициализация сервиса для конкретного преподавателя
        
        Args:
            teacher: Пользователь с ролью 'teacher'
            request: HTTP request для формирования абсолютных URL (опционально)
        """
        if teacher.role != User.Role.TEACHER:
            raise ValueError("Пользователь должен иметь роль 'teacher'")
        
        self.teacher = teacher
        self.request = request
    
    def _build_file_url(self, file_field):
        """Формирует абсолютный URL для файла"""
        if not file_field:
            return None
        if self.request:
            return self.request.build_absolute_uri(file_field.url)
        return file_field.url
    
    @cache_dashboard_data(timeout=900)  # 15 минут
    def get_teacher_students(self) -> List[Dict[str, Any]]:
        """
        Получить список студентов преподавателя
        Исключаем админов (is_staff и is_superuser)
        
        Returns:
            Список словарей с информацией о студентах
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Получаем студентов через SubjectEnrollment (зачисление на предмет)
        # Исключаем админов
        # Используем Prefetch для оптимизации запроса предметов студента
        teacher_enrollments_prefetch = Prefetch(
            'subject_enrollments',
            queryset=SubjectEnrollment.objects.filter(
                teacher=self.teacher,
                is_active=True
            ).select_related('subject'),
            to_attr='teacher_subject_enrollments'
        )
        
        students = User.objects.filter(
            role=User.Role.STUDENT,
            subject_enrollments__teacher=self.teacher,
            subject_enrollments__is_active=True,
            is_staff=False,
            is_superuser=False
        ).distinct().select_related('student_profile').prefetch_related(
            teacher_enrollments_prefetch,
            'assigned_materials__progress',
            'assigned_materials__subject'
        )
        
        logger.info(f"[get_teacher_students] Found {students.count()} students for teacher {self.teacher.username}")
        
        # Получаем материалы преподавателя для статистики
        teacher_materials = Material.objects.filter(
            author=self.teacher,
            status=Material.Status.ACTIVE
        ).values_list('id', flat=True)
        
        # Получаем статистику прогресса одним запросом
        progress_stats = MaterialProgress.objects.filter(
            student__in=students,
            material_id__in=teacher_materials
        ).values('student_id').annotate(
            total_materials=Count('material_id', distinct=True),
            completed_materials=Count('id', filter=Q(is_completed=True))
        )
        
        # Создаем словарь для быстрого поиска статистики
        stats_dict = {
            stat['student_id']: stat 
            for stat in progress_stats
        }
        
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
            except Exception as e:
                logger.warning(f"No profile for student {student.username}: {e}")
                profile_data = {
                    'grade': 'Не указан',
                    'goal': '',
                    'progress_percentage': 0,
                    'streak_days': 0,
                    'total_points': 0,
                    'accuracy_percentage': 0
                }
            
            # Получаем статистику из словаря
            stats = stats_dict.get(student.id, {
                'total_materials': 0,
                'completed_materials': 0
            })
            
            total_materials = stats['total_materials']
            completed_materials = stats['completed_materials']
            
            # Получаем все предметы студента, назначенные этим преподавателем
            # Используем prefetched данные для оптимизации
            teacher_enrollments = getattr(student, 'teacher_subject_enrollments', [])
            if not teacher_enrollments:
                # Fallback: если prefetch не сработал, делаем запрос
                teacher_enrollments = list(student.subject_enrollments.filter(
                    teacher=self.teacher,
                    is_active=True
                ).select_related('subject'))
            
            student_subjects = [
                {
                    'id': enrollment.subject.id,
                    'name': enrollment.get_subject_name(),  # Используем кастомное название, если есть
                    'color': enrollment.subject.color,
                    'enrollment_id': enrollment.id,
                    'enrolled_at': enrollment.enrolled_at,
                    'custom_subject_name': enrollment.custom_subject_name,  # Добавляем кастомное название для отображения
                }
                for enrollment in teacher_enrollments
            ]
            
            result.append({
                'id': student.id,
                'username': student.username,
                'name': student.get_full_name() or student.username,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email or '',
                'avatar': self._build_file_url(student.avatar) if student.avatar else None,
                'profile': profile_data,
                'subjects': student_subjects,  # Добавляем список предметов
                'assigned_materials_count': total_materials,
                'completed_materials_count': completed_materials,
                'completion_percentage': round((completed_materials / total_materials * 100) if total_materials > 0 else 0, 2)
            })
        
        return result
    
    @cache_material_data(timeout=600)  # 10 минут
    def get_teacher_materials(self, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить материалы преподавателя
        
        Args:
            subject_id: ID предмета для фильтрации (опционально)
            
        Returns:
            Список словарей с информацией о материалах
        """
        materials_query = Material.objects.filter(
            author=self.teacher
        ).select_related('subject').prefetch_related(
            'assigned_to',
            'progress'
        )
        
        if subject_id:
            materials_query = materials_query.filter(subject_id=subject_id)
        
        materials = materials_query.order_by('-created_at')
        
        result = []
        for material in materials:
            # Получаем статистику по материалу
            assigned_count = material.assigned_to.count()
            completed_count = MaterialProgress.objects.filter(
                material=material,
                is_completed=True
            ).count()
            
            # Получаем средний прогресс
            avg_progress = MaterialProgress.objects.filter(
                material=material
            ).aggregate(avg_progress=Avg('progress_percentage'))['avg_progress'] or 0
            
            result.append({
                'id': material.id,
                'title': material.title,
                'description': material.description,
                'type': material.type,
                'status': material.status,
                'difficulty_level': material.difficulty_level,
                'subject': {
                    'id': material.subject.id,
                    'name': material.subject.name,
                    'color': material.subject.color
                },
                'file_url': self._build_file_url(material.file) if material.file else None,
                'video_url': material.video_url,
                'tags': material.tags.split(',') if material.tags else [],
                'created_at': material.created_at,
                'published_at': material.published_at,
                'assigned_count': assigned_count,
                'completed_count': completed_count,
                'completion_percentage': round((completed_count / assigned_count * 100) if assigned_count > 0 else 0, 2),
                'average_progress': round(avg_progress, 2)
            })
        
        return result
    
    def distribute_material(self, material_id: int, student_ids: List[int]) -> Dict[str, Any]:
        """
        Распределить материал среди студентов
        
        Args:
            material_id: ID материала
            student_ids: Список ID студентов
            
        Returns:
            Результат операции
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[distribute_material] Material ID: {material_id}, Student IDs: {student_ids}")
        
        try:
            material = Material.objects.get(id=material_id, author=self.teacher)
            logger.info(f"[distribute_material] Material found: {material.title}")
            
            # Получаем студентов, исключая админов
            students = User.objects.filter(
                id__in=student_ids,
                role=User.Role.STUDENT,
                is_staff=False,
                is_superuser=False
            )
            
            logger.info(f"[distribute_material] Found {students.count()} students")
            
            # Назначаем материал студентам
            material.assigned_to.set(students)
            
            # Создаем записи прогресса для новых назначений
            progress_created = 0
            for student in students:
                _, created = MaterialProgress.objects.get_or_create(
                    student=student,
                    material=material
                )
                if created:
                    progress_created += 1
            
            logger.info(f"[distribute_material] Created {progress_created} new progress records")
            
            return {
                'success': True,
                'message': f'Материал "{material.title}" успешно назначен {students.count()} студентам',
                'assigned_count': students.count()
            }
            
        except Material.DoesNotExist:
            return {
                'success': False,
                'message': 'Материал не найден или у вас нет прав на его редактирование'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при назначении материала: {str(e)}'
            }
    
    def get_student_progress_overview(self, student_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получить обзор прогресса студентов
        
        Args:
            student_id: ID конкретного студента (опционально)
            
        Returns:
            Словарь с обзором прогресса
        """
        # Базовый запрос для материалов преподавателя
        teacher_materials = Material.objects.filter(author=self.teacher)
        
        if student_id:
            # Прогресс конкретного студента
            student = User.objects.get(id=student_id, role=User.Role.STUDENT)
            progress_records = MaterialProgress.objects.filter(
                student=student,
                material__in=teacher_materials
            ).select_related('material', 'material__subject')
            
            # Группируем по предметам
            subject_progress = {}
            for progress in progress_records:
                subject_name = progress.material.subject.name
                if subject_name not in subject_progress:
                    subject_progress[subject_name] = {
                        'total_materials': 0,
                        'completed_materials': 0,
                        'average_progress': 0,
                        'total_time_spent': 0
                    }
                
                subject_progress[subject_name]['total_materials'] += 1
                if progress.is_completed:
                    subject_progress[subject_name]['completed_materials'] += 1
                subject_progress[subject_name]['total_time_spent'] += progress.time_spent
            
            # Вычисляем средний прогресс по предметам
            for subject_name, data in subject_progress.items():
                if data['total_materials'] > 0:
                    data['completion_percentage'] = round(
                        (data['completed_materials'] / data['total_materials'] * 100), 2
                    )
                    data['average_progress'] = round(
                        progress_records.filter(material__subject__name=subject_name)
                        .aggregate(avg=Avg('progress_percentage'))['avg'] or 0, 2
                    )
            
            return {
                'student': {
                    'id': student.id,
                    'name': student.get_full_name(),
                    'email': student.email
                },
                'subject_progress': subject_progress,
                'total_materials': progress_records.count(),
                'completed_materials': progress_records.filter(is_completed=True).count(),
                'overall_completion_percentage': round(
                    (progress_records.filter(is_completed=True).count() / progress_records.count() * 100) 
                    if progress_records.count() > 0 else 0, 2
                )
            }
        
        else:
            # Общий обзор по всем студентам
            students = User.objects.filter(
                role=User.Role.STUDENT,
                assigned_materials__author=self.teacher
            ).distinct()
            
            total_students = students.count()
            total_materials = teacher_materials.count()
            
            # Статистика по завершенным материалам
            completed_progress = MaterialProgress.objects.filter(
                material__in=teacher_materials,
                is_completed=True
            )
            
            completed_count = completed_progress.count()
            total_assignments = MaterialProgress.objects.filter(
                material__in=teacher_materials
            ).count()
            
            # Средний прогресс
            avg_progress = MaterialProgress.objects.filter(
                material__in=teacher_materials
            ).aggregate(avg=Avg('progress_percentage'))['avg'] or 0
            
            # Статистика по предметам
            subject_stats = {}
            for material in teacher_materials:
                subject_name = material.subject.name
                if subject_name not in subject_stats:
                    subject_stats[subject_name] = {
                        'total_materials': 0,
                        'assigned_count': 0,
                        'completed_count': 0
                    }
                
                subject_stats[subject_name]['total_materials'] += 1
                subject_stats[subject_name]['assigned_count'] += material.assigned_to.count()
                subject_stats[subject_name]['completed_count'] += MaterialProgress.objects.filter(
                    material=material,
                    is_completed=True
                ).count()
            
            return {
                'total_students': total_students,
                'total_materials': total_materials,
                'total_assignments': total_assignments,
                'completed_assignments': completed_count,
                'completion_percentage': round(
                    (completed_count / total_assignments * 100) if total_assignments > 0 else 0, 2
                ),
                'average_progress': round(avg_progress, 2),
                'subject_statistics': subject_stats
            }
    
    def create_student_report(self, student_id: int, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создать отчет о студенте
        
        Args:
            student_id: ID студента
            report_data: Данные отчета
            
        Returns:
            Результат создания отчета
        """
        try:
            student = User.objects.get(id=student_id, role=User.Role.STUDENT)
            
            # Создаем отчет
            report = StudentReport.objects.create(
                title=report_data.get('title', f'Отчет по студенту {student.get_full_name()}'),
                description=report_data.get('description', ''),
                report_type=report_data.get('type', StudentReport.ReportType.PROGRESS),
                teacher=self.teacher,
                student=student,
                period_start=report_data.get('start_date', timezone.now().date()),
                period_end=report_data.get('end_date', timezone.now().date()),
                content=report_data.get('content', {}),
                progress_percentage=report_data.get('progress_percentage', 0),
                overall_grade=report_data.get('overall_grade', ''),
                recommendations=report_data.get('recommendations', ''),
                concerns=report_data.get('concerns', ''),
                achievements=report_data.get('achievements', ''),
                status=StudentReport.Status.DRAFT
            )
            
            # Генерируем аналитические данные
            self._generate_report_analytics(report, student)
            
            return {
                'success': True,
                'message': 'Отчет успешно создан',
                'report_id': report.id,
                'report_title': report.title,
                'sent_to_parent': bool(report.parent)
            }
            
        except User.DoesNotExist:
            return {
                'success': False,
                'message': 'Студент не найден'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Ошибка при создании отчета: {str(e)}'
            }
    
    def get_teacher_reports(self) -> List[Dict[str, Any]]:
        """
        Получить отчеты преподавателя
        
        Returns:
            Список отчетов преподавателя
        """
        reports = StudentReport.objects.filter(
            teacher=self.teacher
        ).select_related('student', 'parent').order_by('-created_at')
        
        result = []
        for report in reports:
            result.append({
                'id': report.id,
                'title': report.title,
                'description': report.description,
                'report_type': report.report_type,
                'status': report.status,
                'student': {
                    'id': report.student.id,
                    'name': report.student.get_full_name(),
                    'email': report.student.email
                },
                'parent': {
                    'id': report.parent.id,
                    'name': report.parent.get_full_name(),
                    'email': report.parent.email
                } if report.parent else None,
                'period_start': report.period_start,
                'period_end': report.period_end,
                'overall_grade': report.overall_grade,
                'progress_percentage': report.progress_percentage,
                'attendance_percentage': report.attendance_percentage,
                'behavior_rating': report.behavior_rating,
                'recommendations': report.recommendations,
                'concerns': report.concerns,
                'achievements': report.achievements,
                'created_at': report.created_at,
                'sent_at': report.sent_at,
                'read_at': report.read_at
            })
        
        return result
    
    def get_general_chat_access(self) -> Optional[Dict[str, Any]]:
        """
        Получить доступ к общему чату для преподавателей и студентов
        
        Returns:
            Информация о чате или None, если чат не найден
        """
        try:
            # Ищем общий чат
            general_chat = ChatRoom.objects.filter(
                type__in=[ChatRoom.Type.CLASS, 'general'],
                is_active=True
            ).first()
            
            if not general_chat:
                # Если общий чат не существует, создаем его
                general_chat = self._create_general_chat()
            
            # Проверяем, участвует ли преподаватель в чате
            is_participant = general_chat.participants.filter(id=self.teacher.id).exists()
            
            # Получаем последние сообщения
            recent_messages = general_chat.messages.select_related(
                'sender'
            ).order_by('-created_at')[:10]
            
            messages_data = []
            for message in recent_messages:
                messages_data.append({
                    'id': message.id,
                    'content': message.content,
                    'sender': {
                        'id': message.sender.id,
                        'name': message.sender.get_full_name(),
                        'role': message.sender.role
                    },
                    'message_type': message.message_type,
                    'created_at': message.created_at,
                    'is_edited': message.is_edited
                })
            
            return {
                'id': general_chat.id,
                'name': general_chat.name,
                'description': general_chat.description,
                'is_participant': is_participant,
                'participants_count': general_chat.participants.count(),
                'recent_messages': messages_data
            }
            
        except Exception as e:
            print(f"Ошибка при получении доступа к общему чату: {e}")
            return None
    
    def _create_general_chat(self) -> ChatRoom:
        """
        Создать общий чат для преподавателей и студентов
        
        Returns:
            Созданный чат
        """
        # Создаем общий чат
        general_chat = ChatRoom.objects.create(
            name='Общий чат',
            description='Общий чат для преподавателей и студентов',
            type='general',
            created_by=self.teacher
        )
        
        # Добавляем всех студентов и преподавателей
        students_and_teachers = User.objects.filter(
            role__in=[User.Role.STUDENT, User.Role.TEACHER]
        )
        general_chat.participants.set(students_and_teachers)
        
        return general_chat
    
    def _generate_report_analytics(self, report: StudentReport, student: User) -> None:
        """
        Генерировать аналитические данные для отчета
        
        Args:
            report: Объект отчета о студенте
            student: Студент
        """
        try:
            # Получаем материалы преподавателя, назначенные студенту
            teacher_materials = Material.objects.filter(
                author=self.teacher,
                assigned_to=student
            )
            
            # Создаем аналитические данные
            for material in teacher_materials:
                try:
                    progress = MaterialProgress.objects.get(
                        student=student,
                        material=material
                    )
                    
                    # Создаем запись о прогрессе
                    AnalyticsData.objects.create(
                        student=student,
                        metric_type=AnalyticsData.MetricType.STUDENT_PROGRESS,
                        value=float(progress.progress_percentage),
                        unit='%',
                        date=timezone.now().date(),
                        period_start=report.period_start,
                        period_end=report.period_end,
                        metadata={
                            'material_id': material.id,
                            'material_title': material.title,
                            'subject': material.subject.name,
                            'is_completed': progress.is_completed,
                            'time_spent': progress.time_spent
                        }
                    )
                    
                except MaterialProgress.DoesNotExist:
                    # Если прогресса нет, создаем запись с нулевым прогрессом
                    AnalyticsData.objects.create(
                        student=student,
                        metric_type=AnalyticsData.MetricType.STUDENT_PROGRESS,
                        value=0.0,
                        unit='%',
                        date=timezone.now().date(),
                        period_start=report.period_start,
                        period_end=report.period_end,
                        metadata={
                            'material_id': material.id,
                            'material_title': material.title,
                            'subject': material.subject.name,
                            'is_completed': False,
                            'time_spent': 0
                        }
                    )
                    
        except Exception as e:
            print(f"Ошибка при генерации аналитических данных: {e}")
    
    def get_all_subjects(self) -> List[Dict[str, Any]]:
        """
        Получить список всех предметов с признаком, ведет ли их преподаватель
        
        Returns:
            Список предметов с индикатором назначения преподавателю
        """
        import logging
        logger = logging.getLogger(__name__)
        
        from .models import TeacherSubject
        
        teacher_subjects = TeacherSubject.objects.filter(
            teacher=self.teacher,
            is_active=True
        ).select_related('subject')
        assigned_subject_ids = set(ts.subject_id for ts in teacher_subjects)
        
        logger.info(
            "[get_all_subjects] Teacher %s has %d assigned subjects",
            self.teacher.username,
            len(assigned_subject_ids)
        )
        
        result: List[Dict[str, Any]] = []
        for subject in Subject.objects.all().select_related():
            student_count = SubjectEnrollment.objects.filter(
                subject=subject,
                teacher=self.teacher,
                is_active=True
            ).count()
            
            result.append({
                'id': subject.id,
                'name': subject.name,
                'description': subject.description,
                'color': subject.color,
                'student_count': student_count,
                'is_assigned': subject.id in assigned_subject_ids
            })
        
        logger.info(
            "[get_all_subjects] Returning %d subjects for teacher %s",
            len(result),
            self.teacher.username
        )
        return result
    
    def get_subject_students(self, subject_id: int) -> List[Dict[str, Any]]:
        """
        Получить список студентов по предмету
        
        Args:
            subject_id: ID предмета
            
        Returns:
            Список студентов
        """
        enrollments = SubjectEnrollment.objects.filter(
            subject_id=subject_id,
            teacher=self.teacher,
            is_active=True
        ).select_related('student')
        
        result = []
        for enrollment in enrollments:
            try:
                profile = enrollment.student.student_profile
                profile_data = {
                    'grade': profile.grade,
                    'goal': profile.goal,
                    'progress_percentage': profile.progress_percentage
                }
            except:
                profile_data = {
                    'grade': 'Не указан',
                    'goal': '',
                    'progress_percentage': 0
                }
            
            result.append({
                'id': enrollment.student.id,
                'username': enrollment.student.username,
                'name': enrollment.student.get_full_name() or enrollment.student.username,
                'first_name': enrollment.student.first_name,
                'last_name': enrollment.student.last_name,
                'email': enrollment.student.email or '',
                'enrollment_id': enrollment.id,
                'enrolled_at': enrollment.enrolled_at,
                'profile': profile_data
            })
        
        return result
    
    def get_all_students(self) -> List[Dict[str, Any]]:
        """
        Получить список ВСЕХ студентов в системе для назначения предметов
        Исключаем админов (is_staff и is_superuser)
        
        Returns:
            Список всех студентов
        """
        students = User.objects.filter(
            role=User.Role.STUDENT,
            is_active=True,
            is_staff=False,
            is_superuser=False
        ).select_related('student_profile').order_by('username')
        
        result = []
        for student in students:
            try:
                profile = student.student_profile
                profile_data = {
                    'grade': profile.grade,
                    'goal': profile.goal,
                }
            except Exception:
                profile_data = {
                    'grade': 'Не указан',
                    'goal': '',
                }
            
            result.append({
                'id': student.id,
                'username': student.username,
                'name': student.get_full_name() or student.username,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email or '',
                'role': student.role,  # Добавляем роль для фильтрации на фронтенде
                'profile': profile_data
            })
        
        return result
    
    @cache_dashboard_data(timeout=300)  # 5 минут
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Получить полные данные для дашборда преподавателя
        
        Returns:
            Словарь со всеми данными дашборда
        """
        return {
            'teacher_info': {
                'id': self.teacher.id,
                'name': self.teacher.get_full_name(),
                'role': self.teacher.role,
                'avatar': self._build_file_url(self.teacher.avatar) if self.teacher.avatar else None
            },
            'students': self.get_teacher_students(),
            'materials': self.get_teacher_materials(),
            'progress_overview': self.get_student_progress_overview(),
            'reports': self.get_teacher_reports(),
            'general_chat': self.get_general_chat_access()
        }
