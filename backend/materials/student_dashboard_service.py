from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .models import Material, MaterialProgress, Subject, SubjectEnrollment
from chat.models import ChatRoom, Message
from .cache_utils import cache_dashboard_data, cache_material_data, DashboardCacheManager

User = get_user_model()


class StudentDashboardService:
    """
    Сервис для работы с дашбордом студента
    Обеспечивает доступ к материалам, прогрессу и общему чату
    """
    
    def __init__(self, student: User, request=None):
        """
        Инициализация сервиса для конкретного студента
        
        Args:
            student: Пользователь с ролью 'student'
            request: HTTP request для формирования абсолютных URL (опционально)
        """
        if student.role != User.Role.STUDENT:
            raise ValueError("Пользователь должен иметь роль 'student'")
        
        self.student = student
        self.request = request
    
    def _build_file_url(self, file_field):
        """Формирует абсолютный URL для файла"""
        if not file_field:
            return None
        if self.request:
            return self.request.build_absolute_uri(file_field.url)
        return file_field.url
    
    @cache_material_data(timeout=600)  # 10 минут
    def get_assigned_materials(self, subject_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получить назначенные студенту материалы
        
        Args:
            subject_id: ID предмета для фильтрации (опционально)
            
        Returns:
            Список словарей с информацией о материалах и прогрессе
        """
        # Базовый запрос для материалов, назначенных студенту
        materials_query = Material.objects.filter(
            Q(assigned_to=self.student) | Q(is_public=True),
            status=Material.Status.ACTIVE
        ).select_related('subject', 'author').prefetch_related(
            'progress'  # Оптимизация для получения прогресса
        )
        
        # Фильтрация по предмету, если указан
        if subject_id:
            materials_query = materials_query.filter(subject_id=subject_id)
        
        materials = materials_query.order_by('-created_at')
        
        # Получаем все прогрессы студента одним запросом
        progress_dict = {}
        for material in materials:
            for progress in material.progress.all():
                if progress.student_id == self.student.id:
                    progress_dict[material.id] = progress
                    break
        
        result = []
        for material in materials:
            # Получаем прогресс студента по материалу из словаря
            progress = progress_dict.get(material.id)
            if progress:
                progress_data = {
                    'is_completed': progress.is_completed,
                    'progress_percentage': progress.progress_percentage,
                    'time_spent': progress.time_spent,
                    'started_at': progress.started_at,
                    'completed_at': progress.completed_at,
                    'last_accessed': progress.last_accessed
                }
            else:
                progress_data = {
                    'is_completed': False,
                    'progress_percentage': 0,
                    'time_spent': 0,
                    'started_at': None,
                    'completed_at': None,
                    'last_accessed': None
                }
            
            result.append({
                'id': material.id,
                'title': material.title,
                'description': material.description,
                'type': material.type,
                'difficulty_level': material.difficulty_level,
                'subject': {
                    'id': material.subject.id,
                    'name': material.subject.name,
                    'color': material.subject.color
                },
                'author': {
                    'id': material.author.id,
                    'name': material.author.get_full_name(),
                    'role': material.author.role
                },
                'file_url': self._build_file_url(material.file) if material.file else None,
                'video_url': material.video_url,
                'tags': material.tags.split(',') if material.tags else [],
                'created_at': material.created_at,
                'published_at': material.published_at,
                'progress': progress_data
            })
        
        return result
    
    def get_materials_by_subject(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Получить материалы, сгруппированные по предметам
        
        Returns:
            Словарь с ключами - названиями предметов и значениями - списками материалов
        """
        materials = self.get_assigned_materials()
        
        # Группируем материалы по предметам
        subjects_dict = {}
        for material in materials:
            subject_name = material['subject']['name']
            if subject_name not in subjects_dict:
                subjects_dict[subject_name] = {
                    'subject_info': material['subject'],
                    'materials': []
                }
            subjects_dict[subject_name]['materials'].append(material)
        
        return subjects_dict
    
    @cache_dashboard_data(timeout=300)  # 5 минут
    def get_progress_statistics(self) -> Dict[str, Any]:
        """
        Получить статистику прогресса студента
        
        Returns:
            Словарь со статистикой прогресса
        """
        # Получаем все материалы, назначенные студенту с оптимизацией
        assigned_materials = Material.objects.filter(
            Q(assigned_to=self.student) | Q(is_public=True),
            status=Material.Status.ACTIVE
        ).select_related('subject', 'author').prefetch_related('progress')
        
        # Получаем прогресс по всем материалам одним запросом
        progress_records = MaterialProgress.objects.filter(
            student=self.student,
            material__in=assigned_materials
        ).select_related('material__subject')
        
        total_materials = assigned_materials.count()
        
        # Агрегируем статистику одним запросом
        progress_stats = progress_records.aggregate(
            completed_count=Count('id', filter=Q(is_completed=True)),
            in_progress_count=Count('id', filter=Q(is_completed=False, progress_percentage__gt=0)),
            total_time=Sum('time_spent'),
            avg_progress=Avg('progress_percentage')
        )
        
        completed_materials = progress_stats['completed_count'] or 0
        in_progress_materials = progress_stats['in_progress_count'] or 0
        not_started_materials = total_materials - completed_materials - in_progress_materials
        total_time_spent = progress_stats['total_time'] or 0
        avg_progress = progress_stats['avg_progress'] or 0
        
        # Оптимизированная статистика по предметам через аннотации
        from django.db.models import Case, When, IntegerField, Count as CountFunc
        
        subject_stats = assigned_materials.values('subject__name').annotate(
            total=CountFunc('id'),
            completed=CountFunc('progress', filter=Q(
                progress__student=self.student,
                progress__is_completed=True
            )),
            in_progress=CountFunc('progress', filter=Q(
                progress__student=self.student,
                progress__is_completed=False,
                progress__progress_percentage__gt=0
            ))
        ).order_by('subject__name')
        
        # Преобразуем в нужный формат
        subject_stats_dict = {}
        for stat in subject_stats:
            subject_name = stat['subject__name']
            completed = stat['completed']
            in_progress = stat['in_progress']
            total = stat['total']
            not_started = total - completed - in_progress
            
            subject_stats_dict[subject_name] = {
                'total': total,
                'completed': completed,
                'in_progress': in_progress,
                'not_started': not_started
            }
        
        return {
            'total_materials': total_materials,
            'completed_materials': completed_materials,
            'in_progress_materials': in_progress_materials,
            'not_started_materials': not_started_materials,
            'completion_percentage': round((completed_materials / total_materials * 100) if total_materials > 0 else 0, 2),
            'average_progress': round(avg_progress, 2),
            'total_time_spent': total_time_spent,
            'subject_statistics': subject_stats_dict
        }
    
    def get_recent_activity(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Получить недавнюю активность студента
        
        Args:
            days: Количество дней для анализа (по умолчанию 7)
            
        Returns:
            Список активностей за указанный период
        """
        since_date = timezone.now() - timedelta(days=days)
        
        activities = []
        
        # Недавно завершенные материалы
        recent_completions = MaterialProgress.objects.filter(
            student=self.student,
            completed_at__gte=since_date
        ).select_related('material', 'material__subject')
        
        for progress in recent_completions:
            activities.append({
                'id': progress.id,
                'type': 'material_completed',
                'title': progress.material.title,
                'deadline': progress.completed_at.strftime('%Y-%m-%d') if progress.completed_at else '',
                'status': 'completed',
                'description': f'Предмет: {progress.material.subject.name}',
                'timestamp': progress.completed_at,
                'data': {
                    'material_id': progress.material.id,
                    'subject_id': progress.material.subject.id,
                    'progress_percentage': progress.progress_percentage,
                    'time_spent': progress.time_spent
                }
            })
        
        # Недавно начатые материалы
        recent_starts = MaterialProgress.objects.filter(
            student=self.student,
            started_at__gte=since_date,
            is_completed=False
        ).select_related('material', 'material__subject')
        
        for progress in recent_starts:
            # Получаем дедлайн из материала, если есть
            deadline = progress.material.published_at or progress.started_at
            activities.append({
                'id': progress.id,
                'type': 'material_started',
                'title': progress.material.title,
                'deadline': deadline.strftime('%Y-%m-%d') if deadline else '',
                'status': 'pending',
                'description': f'Предмет: {progress.material.subject.name}',
                'timestamp': progress.started_at,
                'data': {
                    'material_id': progress.material.id,
                    'subject_id': progress.material.subject.id,
                    'progress_percentage': progress.progress_percentage
                }
            })
        
        # Сортируем по времени (новые сначала)
        activities.sort(key=lambda x: x['timestamp'] if x.get('timestamp') else timezone.now(), reverse=True)
        
        return activities
    
    def get_general_chat_access(self) -> Optional[Dict[str, Any]]:
        """
        Получить доступ к общему чату для студентов и преподавателей
        
        Returns:
            Информация о чате или None, если чат не найден
        """
        try:
            # Ищем общий чат (тип CLASS или специальный общий чат)
            general_chat = ChatRoom.objects.filter(
                type__in=[ChatRoom.Type.CLASS, 'general'],
                is_active=True
            ).first()
            
            if not general_chat:
                # Если общий чат не существует, создаем его
                general_chat = self._create_general_chat()
            
            # Проверяем, участвует ли студент в чате
            is_participant = general_chat.participants.filter(id=self.student.id).exists()
            
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
            # Логируем ошибку и возвращаем None
            print(f"Ошибка при получении доступа к общему чату: {e}")
            return None
    
    def _create_general_chat(self) -> ChatRoom:
        """
        Создать общий чат для студентов и преподавателей
        
        Returns:
            Созданный чат
        """
        # Создаем общий чат
        general_chat = ChatRoom.objects.create(
            name='Общий чат',
            description='Общий чат для студентов и преподавателей',
            type='general',  # Используем кастомный тип
            created_by=self.student  # Временно, потом можно изменить
        )
        
        # Добавляем всех студентов и преподавателей
        students_and_teachers = User.objects.filter(
            role__in=[User.Role.STUDENT, User.Role.TEACHER]
        )
        general_chat.participants.set(students_and_teachers)
        
        return general_chat
    
    @cache_material_data(timeout=600)  # 10 минут
    def get_subjects(self) -> List[Dict[str, Any]]:
        """
        Получить список предметов студента через зачисления
        
        Returns:
            Список предметов с информацией о зачислениях
        """
        enrollments = SubjectEnrollment.objects.filter(
            student=self.student,
            is_active=True
        ).select_related('subject', 'teacher').order_by('subject__name')
        
        result = []
        for enrollment in enrollments:
            result.append({
                'id': enrollment.subject.id,
                'name': enrollment.get_subject_name(),
                'description': enrollment.subject.description,
                'color': enrollment.subject.color,
                'teacher': {
                    'id': enrollment.teacher.id,
                    'name': enrollment.teacher.get_full_name(),
                    'username': enrollment.teacher.username
                },
                'enrolled_at': enrollment.enrolled_at,
                'enrollment_id': enrollment.id
            })
        
        return result
    
    @cache_dashboard_data(timeout=300)  # 5 минут
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Получить полные данные для дашборда студента
        
        Returns:
            Словарь со всеми данными дашборда
        """
        stats = self.get_progress_statistics()
        
        return {
            'student_info': {
                'id': self.student.id,
                'name': self.student.get_full_name(),
                'username': self.student.username,
                'role': self.student.role,
                'avatar': self._build_file_url(self.student.avatar) if self.student.avatar else None
            },
            'subjects': self.get_subjects(),
            'materials_by_subject': self.get_materials_by_subject(),
            'stats': stats,
            'progress_statistics': stats,
            'recent_activity': self.get_recent_activity(),
            'general_chat': self.get_general_chat_access()
        }
