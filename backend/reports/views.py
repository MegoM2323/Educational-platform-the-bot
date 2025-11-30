from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    Report, ReportTemplate, ReportRecipient, AnalyticsData, ReportSchedule,
    StudentReport, TutorWeeklyReport, TeacherWeeklyReport
)
from .serializers import (
    ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer,
    ReportTemplateSerializer, ReportRecipientSerializer, AnalyticsDataSerializer,
    ReportScheduleSerializer, ReportStatsSerializer, StudentProgressSerializer,
    ClassPerformanceSerializer, StudentReportSerializer, StudentReportCreateSerializer,
    TutorWeeklyReportSerializer, TutorWeeklyReportCreateSerializer,
    TeacherWeeklyReportSerializer, TeacherWeeklyReportCreateSerializer
)
from .student_report_service import StudentReportService
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment
from django.contrib.auth import get_user_model

User = get_user_model()


class ReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet для отчетов
    """
    queryset = Report.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'author', 'is_auto_generated']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'generated_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ReportListSerializer
        elif self.action == 'create':
            return ReportCreateSerializer
        return ReportDetailSerializer
    
    def get_queryset(self):
        """
        Фильтрация отчетов в зависимости от роли пользователя
        """
        user = self.request.user
        
        if user.role == 'student':
            # Студенты видят отчеты о себе
            return Report.objects.filter(target_students=user)
        elif user.role == 'parent':
            # Родители видят отчеты о своих детях
            children = user.parent_profile.children.all()
            return Report.objects.filter(target_students__in=children)
        elif user.role in ['teacher', 'tutor']:
            # Преподаватели и тьюторы видят все отчеты
            return Report.objects.all()
        
        return Report.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """
        Генерировать отчет
        """
        report = self.get_object()
        
        if report.status != Report.Status.DRAFT:
            return Response(
                {'error': 'Отчет уже сгенерирован'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Здесь должна быть логика генерации отчета
        # Пока просто обновляем статус
        report.status = Report.Status.GENERATED
        report.generated_at = timezone.now()
        report.save()
        
        return Response({'message': 'Отчет сгенерирован'})
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Отправить отчет
        """
        report = self.get_object()
        
        if report.status != Report.Status.GENERATED:
            return Response(
                {'error': 'Отчет должен быть сгенерирован перед отправкой'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем получателей
        recipients = []
        for student in report.target_students.all():
            recipients.append(ReportRecipient.objects.create(
                report=report,
                recipient=student
            ))
        
        for parent in report.target_parents.all():
            recipients.append(ReportRecipient.objects.create(
                report=report,
                recipient=parent
            ))
        
        # Обновляем статус
        report.status = Report.Status.SENT
        report.sent_at = timezone.now()
        report.save()
        
        # Отмечаем всех получателей как отправленных
        for recipient in recipients:
            recipient.is_sent = True
            recipient.sent_at = timezone.now()
            recipient.save()
        
        return Response({'message': 'Отчет отправлен'})


class StudentReportViewSet(viewsets.ModelViewSet):
    """CRUD для персональных отчётов студентов преподавателем.

    Требует аутентификации. Преподаватели видят и управляют только своими отчётами.
    Родители/студенты могут читать отчёты о себе (read-only queryset ограничен).
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['report_type', 'status', 'student']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        qs = StudentReport.objects.select_related('teacher', 'student', 'parent')
        if user.role == 'teacher':
            return qs.filter(teacher=user)
        if user.role == 'student':
            return qs.filter(student=user)
        if user.role == 'parent':
            children = getattr(user, 'children', None)
            if children is not None:
                return qs.filter(student__in=children.all())
        return StudentReport.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return StudentReportCreateSerializer
        return StudentReportSerializer

    def perform_create(self, serializer):
        serializer.save()  # teacher подставится в serializer.create

    @action(detail=False, methods=['get'])
    def available_students(self, request):
        """Список студентов, доступных преподавателю для отчётов."""
        if request.user.role != 'teacher':
            return Response({'error': 'Требуется роль преподавателя'}, status=status.HTTP_403_FORBIDDEN)
        students = StudentReportService.get_teacher_students(request.user)
        return Response({'students': students}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """
        Получить аналитические данные для отчета
        """
        report = self.get_object()
        
        # Собираем аналитические данные
        analytics_data = {
            'students_count': report.target_students.count(),
            'parents_count': report.target_parents.count(),
            'period_days': (report.end_date - report.start_date).days,
            'generated_at': report.generated_at,
            'sent_at': report.sent_at
        }
        
        return Response(analytics_data)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet для шаблонов отчетов
    """
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AnalyticsDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для аналитических данных
    """
    queryset = AnalyticsData.objects.all()
    serializer_class = AnalyticsDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'metric_type', 'date']
    ordering_fields = ['date', 'value']
    ordering = ['-date']
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'student':
            return AnalyticsData.objects.filter(student=user)
        elif user.role == 'parent':
            children = user.parent_profile.children.all()
            return AnalyticsData.objects.filter(student__in=children)
        elif user.role in ['teacher', 'tutor']:
            return AnalyticsData.objects.all()
        
        return AnalyticsData.objects.none()


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet для расписания отчетов
    """
    queryset = ReportSchedule.objects.all()
    serializer_class = ReportScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active', 'frequency']
    ordering_fields = ['next_generation', 'created_at']
    ordering = ['next_generation']


class ReportStatsViewSet(viewsets.ViewSet):
    """
    ViewSet для статистики отчетов
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """
        Получить статистику отчетов
        """
        user = request.user
        
        # Базовые статистики
        total_reports = Report.objects.count()
        draft_reports = Report.objects.filter(status=Report.Status.DRAFT).count()
        generated_reports = Report.objects.filter(status=Report.Status.GENERATED).count()
        sent_reports = Report.objects.filter(status=Report.Status.SENT).count()
        auto_generated_reports = Report.objects.filter(is_auto_generated=True).count()
        
        templates_count = ReportTemplate.objects.count()
        active_schedules = ReportSchedule.objects.filter(is_active=True).count()
        
        stats = {
            'total_reports': total_reports,
            'draft_reports': draft_reports,
            'generated_reports': generated_reports,
            'sent_reports': sent_reports,
            'auto_generated_reports': auto_generated_reports,
            'templates_count': templates_count,
            'active_schedules': active_schedules
        }
        
        serializer = ReportStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def student_progress(self, request):
        """
        Получить прогресс студентов
        """
        # Здесь должна быть логика получения прогресса студентов
        # Пока возвращаем заглушку
        progress_data = []
        
        serializer = StudentProgressSerializer(progress_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def class_performance(self, request):
        """
        Получить успеваемость класса
        """
        # Здесь должна быть логика получения успеваемости класса
        # Пока возвращаем заглушку
        performance_data = {}
        
        serializer = ClassPerformanceSerializer(performance_data)
        return Response(serializer.data)


class TutorWeeklyReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet для еженедельных отчетов тьютора родителю
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'student', 'week_start']
    search_fields = ['title', 'summary']
    ordering_fields = ['week_start', 'created_at', 'sent_at']
    ordering = ['-week_start', '-created_at']

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to return JSON response with success message
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'success': True, 'message': 'Отчет успешно удален'},
            status=status.HTTP_200_OK
        )
    
    def get_queryset(self):
        user = self.request.user
        qs = TutorWeeklyReport.objects.select_related(
            'tutor', 'student', 'parent', 'student__student_profile'
        )
        
        if user.role == 'tutor':
            # Тьютор видит только свои отчеты
            return qs.filter(tutor_id=user.id)
        elif user.role == 'parent':
            # Родитель видит только отправленные отчеты о своих детях
            # Проверяем как напрямую через parent, так и через профили детей
            children_ids = list(User.objects.filter(
                student_profile__parent_id=user.id,
                role='student'
            ).values_list('id', flat=True))
            
            # Родитель видит только отправленные отчеты (не черновики)
            if children_ids:
                return qs.filter(
                    (Q(parent_id=user.id) | Q(student_id__in=children_ids)) &
                    ~Q(status=TutorWeeklyReport.Status.DRAFT)
                )
            else:
                # Если нет детей в профилях, фильтруем только по parent и исключаем черновики
                return qs.filter(parent_id=user.id).exclude(status=TutorWeeklyReport.Status.DRAFT)
        elif user.role == 'student':
            # Студент видит отчеты о себе
            return qs.filter(student_id=user.id)
        
        return TutorWeeklyReport.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TutorWeeklyReportCreateSerializer
        return TutorWeeklyReportSerializer
    
    def create(self, request, *args, **kwargs):
        # Только тьюторы могут создавать отчеты
        if request.user.role != 'tutor':
            raise permissions.PermissionDenied("Только тьюторы могут создавать отчеты")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except Exception as e:
            # Обрабатываем ошибки создания отчета
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'detail': 'Отчет с такими параметрами уже существует. Выберите другой период или отредактируйте существующий отчет.'
                })
            raise
        
        # Используем основной сериализатор для возврата полных данных
        instance = serializer.instance
        output_serializer = TutorWeeklyReportSerializer(instance, context={'request': request})
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        # tutor уже устанавливается в сериализаторе
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Отправить отчет родителю
        """
        report = self.get_object()
        
        if report.status != TutorWeeklyReport.Status.DRAFT:
            return Response(
                {'error': 'Отчет уже отправлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.user.id != report.tutor_id:
            return Response(
                {'error': 'Вы не можете отправить этот отчет'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что родитель назначен
        if not report.parent_id:
            # Попытаемся получить родителя из профиля студента
            try:
                student_profile = StudentProfile.objects.select_related('parent').get(user_id=report.student_id)
                if student_profile.parent_id:
                    report.parent_id = student_profile.parent_id
                else:
                    return Response(
                        {'error': 'Не указан родитель для студента. Отчет не может быть отправлен.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except StudentProfile.DoesNotExist:
                return Response(
                    {'error': 'Профиль студента не найден. Отчет не может быть отправлен.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        report.status = TutorWeeklyReport.Status.SENT
        report.sent_at = timezone.now()
        report.save()
        
        # Возвращаем обновленный отчет с сериализатором
        from .serializers import TutorWeeklyReportSerializer
        serializer = TutorWeeklyReportSerializer(report)
        return Response({
            'message': 'Отчет отправлен родителю',
            'report': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Отметить отчет как прочитанный (для родителя)
        """
        report = self.get_object()
        
        if request.user.role != 'parent':
            return Response(
                {'error': 'Только родитель может отметить отчет как прочитанный'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что отчет принадлежит этому родителю
        is_authorized = False
        
        # Проверяем напрямую через поле parent
        if report.parent_id and report.parent_id == request.user.id:
            is_authorized = True
        else:
            # Также проверяем через профиль студента
            try:
                student_profile = StudentProfile.objects.select_related('parent').get(user_id=report.student_id)
                if student_profile.parent_id and student_profile.parent_id == request.user.id:
                    is_authorized = True
            except StudentProfile.DoesNotExist:
                pass
        
        if not is_authorized:
            return Response(
                {'error': 'Вы не можете отметить этот отчет как прочитанный'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if report.status == TutorWeeklyReport.Status.SENT:
            report.status = TutorWeeklyReport.Status.READ
            report.read_at = timezone.now()
            report.save()
        
        return Response({'message': 'Отчет отмечен как прочитанный'})
    
    @action(detail=False, methods=['get'])
    def available_students(self, request):
        """
        Список студентов тьютора для создания отчетов
        """
        if request.user.role != 'tutor':
            return Response(
                {'error': 'Требуется роль тьютора'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        students = User.objects.filter(
            student_profile__tutor_id=request.user.id,
            role='student'
        ).select_related('student_profile', 'student_profile__parent').distinct()
        
        students_data = []
        for student in students:
            try:
                parent = None
                grade = ''
                try:
                    student_profile = student.student_profile
                    grade = student_profile.grade or ''
                    parent = student_profile.parent
                except StudentProfile.DoesNotExist:
                    pass
                
                students_data.append({
                    'id': student.id,
                    'name': student.get_full_name(),
                    'username': student.username,
                    'grade': grade,
                    'parent_id': parent.id if parent else None,
                    'parent_name': parent.get_full_name() if parent else None,
                })
            except Exception:
                # Пропускаем студента, если есть ошибки при получении данных
                continue
        
        return Response({'students': students_data})


class TeacherWeeklyReportViewSet(viewsets.ModelViewSet):
    """
    ViewSet для еженедельных отчетов преподавателя тьютору
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'student', 'subject', 'week_start']
    search_fields = ['title', 'summary']
    ordering_fields = ['week_start', 'created_at', 'sent_at']
    ordering = ['-week_start', '-created_at']

    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to return JSON response with success message
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {'success': True, 'message': 'Отчет успешно удален'},
            status=status.HTTP_200_OK
        )
    
    def get_queryset(self):
        user = self.request.user
        qs = TeacherWeeklyReport.objects.select_related(
            'teacher', 'student', 'tutor', 'subject', 'student__student_profile'
        )
        
        if user.role == 'teacher':
            # Преподаватель видит только свои отчеты
            return qs.filter(teacher_id=user.id)
        elif user.role == 'tutor':
            # Тьютор видит отчеты о своих студентах
            # Проверяем как напрямую через tutor, так и через профили студентов
            students_ids = list(User.objects.filter(
                student_profile__tutor_id=user.id,
                role='student'
            ).values_list('id', flat=True))
            
            # Если есть студенты, фильтруем по tutor или по студентам
            # Тьютор видит все отчеты о своих студентах (включая отправленные и черновики)
            if students_ids:
                return qs.filter(Q(tutor_id=user.id) | Q(student_id__in=students_ids))
            else:
                # Если нет студентов в профилях, фильтруем только по tutor
                return qs.filter(tutor_id=user.id)
        elif user.role == 'student':
            # Студент видит отчеты о себе
            return qs.filter(student_id=user.id)
        
        return TeacherWeeklyReport.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TeacherWeeklyReportCreateSerializer
        return TeacherWeeklyReportSerializer
    
    def create(self, request, *args, **kwargs):
        # Только преподаватели могут создавать отчеты
        if request.user.role != 'teacher':
            raise permissions.PermissionDenied("Только преподаватели могут создавать отчеты")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except Exception as e:
            # Обрабатываем ошибки создания отчета
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({
                    'detail': 'Отчет с такими параметрами уже существует. Выберите другой период или отредактируйте существующий отчет.'
                })
            raise
        
        # Используем основной сериализатор для возврата полных данных
        instance = serializer.instance
        output_serializer = TeacherWeeklyReportSerializer(instance, context={'request': request})
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        # teacher уже устанавливается в сериализаторе
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Отправить отчет тьютору
        """
        report = self.get_object()
        
        if report.status != TeacherWeeklyReport.Status.DRAFT:
            return Response(
                {'error': 'Отчет уже отправлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.user.id != report.teacher_id:
            return Response(
                {'error': 'Вы не можете отправить этот отчет'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что тьютор назначен (опционально, но желательно)
        if not report.tutor_id:
            # Попытаемся получить тьютора из профиля студента
            try:
                student_profile = StudentProfile.objects.select_related('tutor').get(user_id=report.student_id)
                if student_profile.tutor_id:
                    report.tutor_id = student_profile.tutor_id
            except StudentProfile.DoesNotExist:
                pass
            # Если тьютор все еще не назначен, все равно отправляем отчет
            # (тьютор может быть назначен позже, отчет будет виден через фильтрацию по студенту)
        
        report.status = TeacherWeeklyReport.Status.SENT
        report.sent_at = timezone.now()
        report.save()
        
        # Возвращаем обновленный отчет с сериализатором
        from .serializers import TeacherWeeklyReportSerializer
        serializer = TeacherWeeklyReportSerializer(report)
        return Response({
            'message': 'Отчет отправлен тьютору',
            'report': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Отметить отчет как прочитанный (для тьютора)
        """
        report = self.get_object()
        
        if request.user.role != 'tutor':
            return Response(
                {'error': 'Только тьютор может отметить отчет как прочитанный'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что отчет принадлежит этому тьютору
        is_authorized = False
        
        # Проверяем напрямую через поле tutor
        if report.tutor_id and report.tutor_id == request.user.id:
            is_authorized = True
        else:
            # Также проверяем через профиль студента
            try:
                student_profile = StudentProfile.objects.select_related('tutor').get(user_id=report.student_id)
                if student_profile.tutor_id and student_profile.tutor_id == request.user.id:
                    is_authorized = True
            except StudentProfile.DoesNotExist:
                pass
        
        if not is_authorized:
            return Response(
                {'error': 'Вы не можете отметить этот отчет как прочитанный'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if report.status == TeacherWeeklyReport.Status.SENT:
            report.status = TeacherWeeklyReport.Status.READ
            report.read_at = timezone.now()
            report.save()
        
        return Response({'message': 'Отчет отмечен как прочитанный'})
    
    @action(detail=False, methods=['get'])
    def available_students(self, request):
        """
        Список студентов преподавателя для создания отчетов
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Требуется роль преподавателя'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем студентов через SubjectEnrollment
        enrollments = SubjectEnrollment.objects.filter(
            teacher=request.user,
            is_active=True
        ).select_related('student', 'subject', 'student__student_profile', 'student__student_profile__tutor').distinct()
        
        students_data = []
        seen_students = set()
        
        for enrollment in enrollments:
            student = enrollment.student
            if student.id not in seen_students:
                seen_students.add(student.id)
                tutor = None
                grade = ''
                
                try:
                    student_profile = student.student_profile
                    grade = student_profile.grade or ''
                    tutor = student_profile.tutor
                except StudentProfile.DoesNotExist:
                    pass
                
                students_data.append({
                    'id': student.id,
                    'name': student.get_full_name(),
                    'username': student.username,
                    'grade': grade,
                    'tutor_id': tutor.id if tutor else None,
                    'tutor_name': tutor.get_full_name() if tutor else None,
                    'subjects': []
                })
        
        # Добавляем предметы для каждого студента
        for enrollment in enrollments:
            for student_data in students_data:
                if student_data['id'] == enrollment.student.id:
                    try:
                        subject_name = enrollment.get_subject_name()
                    except (AttributeError, Exception):
                        # Fallback на стандартное название предмета
                        subject_name = enrollment.subject.name
                    
                    student_data['subjects'].append({
                        'id': enrollment.subject.id,
                        'name': subject_name,
                        'color': enrollment.subject.color
                    })
        
        return Response({'students': students_data})
    
    @action(detail=False, methods=['get'])
    def by_student(self, request):
        """
        Получить все отчеты преподавателей по конкретному студенту (для тьютора)
        """
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response(
                {'error': 'Не указан student_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.user.role != 'tutor':
            return Response(
                {'error': 'Требуется роль тьютора'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем, что студент закреплен за этим тьютором
        try:
            student_profile = StudentProfile.objects.select_related('tutor').get(
                user_id=student_id,
                tutor_id=request.user.id
            )
        except StudentProfile.DoesNotExist:
            return Response(
                {'error': 'Студент не закреплен за вами'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем отчеты, где тьютор указан напрямую или через профиль студента
        reports = TeacherWeeklyReport.objects.filter(
            student_id=student_id
        ).filter(
            Q(tutor_id=request.user.id) | Q(student__student_profile__tutor_id=request.user.id)
        ).select_related('teacher', 'student', 'subject', 'tutor', 'student__student_profile').order_by('-week_start')
        
        serializer = TeacherWeeklyReportSerializer(reports, many=True)
        return Response(serializer.data)