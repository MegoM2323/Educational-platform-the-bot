from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Subject, Material, MaterialProgress, MaterialComment, MaterialSubmission, MaterialFeedback
from .models import SubjectEnrollment, TeacherSubject
from notifications.notification_service import NotificationService
from .serializers import (
    SubjectSerializer, MaterialListSerializer, MaterialDetailSerializer,
    MaterialCreateSerializer, MaterialProgressSerializer, MaterialCommentSerializer,
    MaterialSubmissionSerializer, MaterialFeedbackSerializer
)


class SubjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet для предметов
    """
    queryset = Subject.objects.all().prefetch_related('subject_teachers')
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def teachers(self, request, pk=None):
        """
        Получить преподавателей, которые ведут этот предмет
        """
        subject = self.get_object()
        
        # Получаем преподавателей через модель TeacherSubject
        teacher_subjects = TeacherSubject.objects.filter(
            subject=subject,
            is_active=True
        ).select_related('teacher')
        
        teacher_ids = [ts.teacher.id for ts in teacher_subjects]
        teachers = User.objects.filter(
            id__in=teacher_ids,
            role=User.Role.TEACHER
        )
        
        from accounts.serializers import UserSerializer
        serializer = UserSerializer(teachers, many=True)
        return Response(serializer.data)


class MaterialViewSet(viewsets.ModelViewSet):
    """
    ViewSet для материалов
    """
    queryset = Material.objects.all().select_related('author', 'subject').prefetch_related('assigned_to', 'progress')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'type', 'status', 'author', 'difficulty_level']
    search_fields = ['title', 'description', 'content', 'tags']
    ordering_fields = ['created_at', 'updated_at', 'title', 'difficulty_level']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MaterialListSerializer
        elif self.action == 'create':
            return MaterialCreateSerializer
        return MaterialDetailSerializer
    
    def get_queryset(self):
        """
        Фильтрация материалов в зависимости от роли пользователя
        """
        user = self.request.user
        base_queryset = Material.objects.select_related('author', 'subject').prefetch_related('assigned_to', 'progress')

        if user.role == 'student':
            # Студенты видят только назначенные им материалы или публичные
            return base_queryset.filter(
                Q(assigned_to=user) | Q(is_public=True)
            ).distinct()
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели и тьюторы видят все материалы
            return base_queryset
        elif user.role == 'parent':
            # Родители видят материалы своих детей
            children = user.parent_profile.children.all()
            return base_queryset.filter(assigned_to__in=children).distinct()

        return Material.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Создание материала преподавателем с пост-обработкой:
        - Проверка роли (teacher/tutor)
        - Сохранение материала
        - Создание прогресса для назначенных студентов
        - Уведомление назначенных студентов при статусе ACTIVE
        """
        user = request.user
        # Разрешаем создавать материалы только преподавателю/тьютору
        if getattr(user, 'role', None) not in ['teacher', 'tutor']:
            return Response(
                {'error': 'Создавать материалы могут только преподаватели и тьюторы'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Сохраняем материал с автором
        self.perform_create(serializer)

        # На этом этапе материал создан. Получаем экземпляр
        material = serializer.instance

        # Создаем прогресс для назначенных студентов (если были переданы)
        try:
            assigned_students = material.assigned_to.all()
            for student in assigned_students:
                MaterialProgress.objects.get_or_create(student=student, material=material)
        except Exception:
            # Не прерываем создание материала из-за ошибки прогресса
            pass

        # Если материал активен — уведомляем назначенных студентов
        if material.status == Material.Status.ACTIVE:
            try:
                notifier = NotificationService()
                for student in assigned_students:
                    try:
                        notifier.notify_material_published(
                            student=student,
                            material_id=material.id,
                            subject_id=material.subject_id,
                        )
                    except Exception:
                        # Продолжаем даже если конкретное уведомление не ушло
                        pass
            except Exception:
                pass

        # Возвращаем детальные данные, включая id, assigned_to и т.д.
        detail_data = MaterialDetailSerializer(material, context={'request': request}).data
        headers = self.get_success_headers(detail_data)
        return Response(detail_data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """
        Назначить материал студентам
        """
        material = self.get_object()
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids:
            return Response(
                {'error': 'Не указаны ID студентов'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, что все указанные пользователи - студенты
        from django.contrib.auth import get_user_model
        User = get_user_model()
        students = User.objects.filter(
            id__in=student_ids,
            role=User.Role.STUDENT
        )
        
        if len(students) != len(student_ids):
            return Response(
                {'error': 'Некоторые пользователи не являются студентами'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        material.assigned_to.set(students)

        # Отправляем уведомления назначенным студентам о новом материале
        notifier = NotificationService()
        for student in students:
            try:
                notifier.notify_material_published(
                    student=student,
                    material_id=material.id,
                    subject_id=material.subject_id,
                )
            except Exception:
                # Не прерываем процесс назначения из-за ошибки уведомления
                pass

        return Response({'message': 'Материал назначен студентам', 'assigned_count': students.count()})
    
    @action(detail=True, methods=['post'])
    def update_progress(self, request, pk=None):
        """
        Обновить прогресс изучения материала
        """
        material = self.get_object()
        student = request.user
        
        if student.role != 'student':
            return Response(
                {'error': 'Только студенты могут обновлять прогресс'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        progress_percentage = request.data.get('progress_percentage', 0)
        time_spent = request.data.get('time_spent', 0)
        
        progress, created = MaterialProgress.objects.get_or_create(
            student=student,
            material=material
        )
        
        progress.progress_percentage = progress_percentage
        progress.time_spent += time_spent
        
        if progress_percentage >= 100:
            progress.is_completed = True
            progress.completed_at = timezone.now()
        
        progress.save()
        
        return Response(MaterialProgressSerializer(progress).data)
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """
        Получить прогресс изучения материала
        """
        material = self.get_object()
        
        if request.user.role == 'student':
            try:
                progress = material.progress.get(student=request.user)
                return Response(MaterialProgressSerializer(progress).data)
            except MaterialProgress.DoesNotExist:
                return Response({'message': 'Прогресс не найден'})
        
        # Для преподавателей и тьюторов показываем прогресс всех студентов
        progress_list = material.progress.all()
        return Response(MaterialProgressSerializer(progress_list, many=True).data)
    
    @action(detail=True, methods=['get', 'post'])
    def comments(self, request, pk=None):
        """
        Получить или добавить комментарии к материалу
        """
        material = self.get_object()
        
        if request.method == 'GET':
            comments = material.comments.select_related('author', 'material').all()
            return Response(MaterialCommentSerializer(comments, many=True).data)
        
        elif request.method == 'POST':
            serializer = MaterialCommentSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save(material=material)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def student_materials(self, request):
        """
        Получить все материалы, назначенные студенту
        """
        if request.user.role != 'student':
            return Response(
                {'error': 'Доступно только для студентов'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем материалы, назначенные студенту или публичные
        materials = Material.objects.filter(
            Q(assigned_to=request.user) | Q(is_public=True),
            status=Material.Status.ACTIVE
        ).distinct().select_related('author', 'subject').prefetch_related('progress')
        
        # Применяем фильтры
        subject_id = request.query_params.get('subject_id')
        material_type = request.query_params.get('type')
        difficulty = request.query_params.get('difficulty')
        
        if subject_id:
            materials = materials.filter(subject_id=subject_id)
        if material_type:
            materials = materials.filter(type=material_type)
        if difficulty:
            materials = materials.filter(difficulty_level=difficulty)
        
        # Сортируем по дате создания (новые сначала)
        materials = materials.order_by('-created_at')
        
        serializer = MaterialListSerializer(materials, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download_file(self, request, pk=None):
        """
        Скачать файл материала
        """
        material = self.get_object()
        
        # Проверяем права доступа
        if not (material.is_public or material.assigned_to.filter(id=request.user.id).exists()):
            return Response(
                {'error': 'Нет доступа к этому материалу'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not material.file:
            return Response(
                {'error': 'Файл не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Обновляем прогресс при скачивании
        if request.user.role == 'student':
            progress, created = MaterialProgress.objects.get_or_create(
                student=request.user,
                material=material
            )
            progress.last_accessed = timezone.now()
            progress.save()
        
        from django.http import FileResponse
        return FileResponse(
            material.file,
            as_attachment=True,
            filename=material.file.name.split('/')[-1]
        )
    
    @action(detail=False, methods=['get'])
    def student_materials(self, request):
        """
        Получить материалы, назначенные студенту
        """
        if request.user.role != 'student':
            return Response(
                {'error': 'Доступно только для студентов'},
                status=status.HTTP_403_FORBIDDEN
            )

        materials = Material.objects.filter(
            Q(assigned_to=request.user) | Q(is_public=True)
        ).distinct().select_related('author', 'subject').prefetch_related('progress').order_by('-created_at')

        serializer = MaterialListSerializer(materials, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """
        Получить ответы студентов на материал
        """
        material = self.get_object()
        
        # Проверяем права доступа
        if request.user.role not in ['teacher', 'tutor']:
            return Response(
                {'error': 'Доступно только для преподавателей'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        submissions = MaterialSubmission.objects.filter(material=material).select_related('student', 'material')
        serializer = MaterialSubmissionSerializer(submissions, many=True, context={'request': request})
        return Response(serializer.data)


class MaterialProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра прогресса материалов
    """
    queryset = MaterialProgress.objects.all().select_related('student', 'material', 'material__subject', 'material__author')
    serializer_class = MaterialProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_queryset = MaterialProgress.objects.select_related('student', 'material', 'material__subject', 'material__author')

        if user.role == 'student':
            return base_queryset.filter(student=user)
        elif user.role in ['teacher', 'tutor']:
            return base_queryset
        elif user.role == 'parent':
            children = user.parent_profile.children.all()
            return base_queryset.filter(student__in=children)

        return MaterialProgress.objects.none()


class MaterialCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для комментариев к материалам
    """
    queryset = MaterialComment.objects.all().select_related('author', 'material', 'material__subject')
    serializer_class = MaterialCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MaterialSubmissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для ответов учеников на материалы
    """
    queryset = MaterialSubmission.objects.all().select_related('student', 'material', 'material__subject', 'material__author').prefetch_related('feedback')
    serializer_class = MaterialSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['material', 'student', 'is_late']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']

    def get_queryset(self):
        """
        Фильтрация ответов в зависимости от роли пользователя
        """
        user = self.request.user
        base_queryset = MaterialSubmission.objects.select_related('student', 'material', 'material__subject', 'material__author').prefetch_related('feedback')

        if user.role == 'student':
            # Студенты видят только свои ответы
            return base_queryset.filter(student=user)
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели видят все ответы
            return base_queryset
        elif user.role == 'parent':
            # Родители видят ответы своих детей
            children = user.parent_profile.children.all()
            return base_queryset.filter(student__in=children)

        return MaterialSubmission.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
    
    @action(detail=False, methods=['post'])
    def submit_answer(self, request):
        """
        Отправить ответ на материал
        """
        if request.user.role != 'student':
            return Response(
                {'error': 'Доступно только для студентов'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        material_id = request.data.get('material_id')
        if not material_id:
            return Response(
                {'error': 'Необходимо указать material_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            material = Material.objects.get(id=material_id)
        except Material.DoesNotExist:
            return Response(
                {'error': 'Материал не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Проверяем, назначен ли материал студенту
        if not (material.is_public or material.assigned_to.filter(id=request.user.id).exists()):
            return Response(
                {'error': 'Материал не назначен вам'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, не отправлял ли уже ответ
        if MaterialSubmission.objects.filter(material=material, student=request.user).exists():
            return Response(
                {'error': 'Ответ уже отправлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MaterialSubmissionSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            submission = serializer.save(material=material, student=request.user)

            # Уведомляем всех преподавателей, закреплённых за предметом этого студента
            try:
                enrollments = SubjectEnrollment.objects.filter(
                    student=request.user,
                    subject=material.subject,
                    is_active=True,
                ).select_related('teacher')
                notifier = NotificationService()
                for enrollment in enrollments:
                    try:
                        notifier.notify_homework_submitted(
                            teacher=enrollment.teacher,
                            submission_id=submission.id,
                            student=request.user,
                        )
                    except Exception:
                        # Продолжаем, если уведомление не удалось отправить
                        pass
            except Exception:
                pass

            # Обновляем статус при наличии фидбэка
            if hasattr(submission, 'feedback'):
                submission.status = MaterialSubmission.Status.REVIEWED
                submission.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit_feedback(self, request, pk=None):
        """
        Добавить фидбэк к ответу ученика
        """
        submission = self.get_object()
        
        if request.user.role not in ['teacher', 'tutor']:
            return Response(
                {'error': 'Только преподаватели могут оставлять фидбэк'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, не существует ли уже фидбэк
        if hasattr(submission, 'feedback'):
            return Response(
                {'error': 'Фидбэк уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MaterialFeedbackSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save(submission=submission)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MaterialFeedbackViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра фидбэка по материалам
    """
    queryset = MaterialFeedback.objects.all().select_related('submission', 'submission__student', 'submission__material', 'submission__material__subject')
    serializer_class = MaterialFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Фильтрация фидбэка в зависимости от роли пользователя
        """
        user = self.request.user
        base_queryset = MaterialFeedback.objects.select_related('submission', 'submission__student', 'submission__material', 'submission__material__subject')

        if user.role == 'student':
            # Студенты видят фидбэк по своим ответам
            return base_queryset.filter(submission__student=user)
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели видят весь фидбэк
            return base_queryset
        elif user.role == 'parent':
            # Родители видят фидбэк по ответам своих детей
            children = user.parent_profile.children.all()
            return base_queryset.filter(submission__student__in=children)

        return MaterialFeedback.objects.none()