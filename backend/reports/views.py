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
    StudentReport, TutorWeeklyReport, TeacherWeeklyReport, ParentReportPreference
)
from .serializers import (
    ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer,
    ReportTemplateSerializer, ReportRecipientSerializer, AnalyticsDataSerializer,
    ReportScheduleSerializer, ReportStatsSerializer, StudentProgressSerializer,
    ClassPerformanceSerializer, StudentReportSerializer, StudentReportCreateSerializer,
    TutorWeeklyReportSerializer, TutorWeeklyReportCreateSerializer,
    TeacherWeeklyReportSerializer, TeacherWeeklyReportCreateSerializer,
    ParentReportPreferenceSerializer
)
from .permissions import ParentReportPermission, IsTeacherOrAdmin, CanAcknowledgeReport
from .student_report_service import StudentReportService, CreateStudentReportInput
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
    permission_classes = [permissions.IsAuthenticated, ParentReportPermission]
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
            # Get reports for children from StudentProfile
            children = User.objects.filter(
                student_profile__parent_id=user.id,
                role='student'
            ).values_list('id', flat=True)

            if children:
                return qs.filter(
                    Q(student_id__in=children, show_to_parent=True) |
                    Q(parent_id=user.id, show_to_parent=True)
                )
            else:
                return qs.filter(parent_id=user.id, show_to_parent=True)
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

    @action(detail=False, methods=['get'])
    def my_children(self, request):
        """Список отчетов о детях родителя."""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Требуется роль родителя'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get children from StudentProfile
        children = User.objects.filter(
            student_profile__parent_id=request.user.id,
            role='student'
        ).values_list('id', flat=True)

        # Get reports that are visible to parent
        reports = StudentReport.objects.filter(
            Q(student_id__in=children, show_to_parent=True) |
            Q(parent_id=request.user.id, show_to_parent=True)
        ).select_related('teacher', 'student', 'parent').order_by('-created_at')

        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Родитель подтверждает прочтение отчета."""
        report = self.get_object()
        permission = CanAcknowledgeReport()

        if not permission.has_object_permission(request, self, report):
            return Response(
                {'error': 'Вы не можете подтвердить этот отчет'},
                status=status.HTTP_403_FORBIDDEN
            )

        report.parent_acknowledged = True
        report.parent_acknowledged_at = timezone.now()
        report.save(update_fields=['parent_acknowledged', 'parent_acknowledged_at'])

        serializer = self.get_serializer(report)
        return Response({
            'message': 'Отчет подтвержден',
            'report': serializer.data
        }, status=status.HTTP_200_OK)

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

    @action(detail=False, methods=['post'], url_path='generate-progress-report')
    def generate_progress_report(self, request):
        """
        Сгенерировать детальный отчёт о прогрессе студента за период.

        Request body:
        {
            "student_id": 123,
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "title": "Monthly Progress Report",
            "description": "Progress tracking for January"
        }

        Returns:
        {
            "report": {...},
            "progress_data": {...}
        }
        """
        from datetime import datetime

        if request.user.role not in ['teacher', 'tutor', 'admin']:
            return Response(
                {'error': 'Требуется роль преподавателя, тьютора или администратора'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse request data
        student_id = request.data.get('student_id')
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        title = request.data.get('title', 'Student Progress Report')
        description = request.data.get('description', '')

        # Validate required fields
        if not student_id or not period_start or not period_end:
            return Response(
                {'error': 'Required fields: student_id, period_start, period_end'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get student
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate student is accessible to current user
        if request.user.role == 'teacher':
            is_student_of_teacher = SubjectEnrollment.objects.filter(
                teacher=request.user,
                student=student,
                is_active=True,
            ).exists()
            if not is_student_of_teacher:
                return Response(
                    {'error': 'Student is not in your classes'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Parse dates
        try:
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate progress data
        try:
            progress_data = StudentReportService.get_student_progress_data(
                student, start_date, end_date
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate progress data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Create StudentReport with generated data
        try:
            report_input = CreateStudentReportInput(
                teacher=request.user,
                student=student,
                title=title,
                period_start=period_start,
                period_end=period_end,
                content=progress_data,
                description=description,
                report_type=StudentReport.ReportType.PROGRESS,
                overall_grade=progress_data['summary']['overall_grade'],
                progress_percentage=int(progress_data['summary']['overall_progress_percentage']),
            )
            report = StudentReportService.create_student_report(report_input)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to create report: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Serialize and return
        serializer = StudentReportSerializer(report)
        return Response({
            'report': serializer.data,
            'progress_data': progress_data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='get-student-progress')
    def get_student_progress(self, request):
        """
        Получить данные прогресса студента за период (без создания отчёта).

        Query params:
        - student_id: ID студента (обязательный)
        - period_start: Начало периода в формате YYYY-MM-DD (обязательный)
        - period_end: Конец периода в формате YYYY-MM-DD (обязательный)

        Returns:
        {
            "progress_data": {...}
        }
        """
        from datetime import datetime

        # Get parameters
        student_id = request.query_params.get('student_id')
        period_start = request.query_params.get('period_start')
        period_end = request.query_params.get('period_end')

        # Validate required fields
        if not student_id or not period_start or not period_end:
            return Response(
                {'error': 'Required params: student_id, period_start, period_end'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get student
        try:
            student = User.objects.get(id=student_id, role='student')
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate student is accessible to current user
        if request.user.role == 'teacher':
            is_student_of_teacher = SubjectEnrollment.objects.filter(
                teacher=request.user,
                student=student,
                is_active=True,
            ).exists()
            if not is_student_of_teacher:
                return Response(
                    {'error': 'Student is not in your classes'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif request.user.role == 'student' and request.user.id != student_id:
            return Response(
                {'error': 'You can only view your own progress'},
                status=status.HTTP_403_FORBIDDEN
            )
        elif request.user.role == 'parent':
            # Check if student is in parent's children
            is_parent_of_student = User.objects.filter(
                id=student_id,
                student_profile__parent_id=request.user.id
            ).exists()
            if not is_parent_of_student:
                return Response(
                    {'error': 'Student is not your child'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Parse dates
        try:
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate progress data
        try:
            progress_data = StudentReportService.get_student_progress_data(
                student, start_date, end_date
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate progress data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({'progress_data': progress_data}, status=status.HTTP_200_OK)


class ParentReportPreferenceViewSet(viewsets.ViewSet):
    """
    Управление настройками видимости отчетов для родителя.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get', 'put'], url_path='my-settings')
    def my_settings(self, request):
        """Получить или обновить настройки текущего родителя."""
        if request.user.role != 'parent':
            return Response(
                {'error': 'Требуется роль родителя'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get or create preferences
        preferences, created = ParentReportPreference.objects.get_or_create(
            parent=request.user
        )

        if request.method == 'GET':
            serializer = ParentReportPreferenceSerializer(preferences)
            return Response(serializer.data)

        elif request.method == 'PUT':
            serializer = ParentReportPreferenceSerializer(
                preferences,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for configurable report templates.
    Supports template inheritance, versioning, and custom section/layout configuration.

    Endpoints:
    - POST /api/reports/templates/ - Create template
    - GET /api/reports/templates/ - List templates
    - GET /api/reports/templates/{id}/ - Retrieve template
    - PATCH /api/reports/templates/{id}/ - Partial update
    - PUT /api/reports/templates/{id}/ - Full update
    - DELETE /api/reports/templates/{id}/ - Delete template
    - POST /api/reports/templates/{id}/create_version/ - Create new version
    - POST /api/reports/templates/{id}/archive/ - Archive template
    - GET /api/reports/templates/{id}/versions/ - List versions
    - GET /api/reports/templates/{id}/children/ - List child templates
    - POST /api/reports/templates/{id}/validate_sections/ - Validate sections config
    - POST /api/reports/templates/{id}/validate_layout/ - Validate layout config
    """
    queryset = ReportTemplate.objects.select_related('created_by', 'parent_template', 'previous_version')
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_default', 'is_archived', 'created_by']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'version']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """Create template with current user as creator."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def create_version(self, request, pk=None):
        """
        Create a new version of this template.

        Request body (optional):
        {
            "name": "Updated Template Name",
            "description": "Updated description",
            "sections": [...],
            "layout_config": {...}
        }
        """
        template = self.get_object()

        # Get overrides from request data
        overrides = {}
        if request.data:
            allowed_fields = ['name', 'description', 'sections', 'layout_config', 'default_format']
            overrides = {k: v for k, v in request.data.items() if k in allowed_fields}

        try:
            new_version = template.create_version(**overrides)
            serializer = self.get_serializer(new_version)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': f'Failed to create version: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        Archive this template and all child templates.

        When archived, template is hidden from normal listings but kept for historical reference.
        """
        template = self.get_object()

        if template.is_archived:
            return Response(
                {'error': 'Template is already archived'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        template.is_archived = True
        template.archived_at = timezone.now()
        template.save()

        serializer = self.get_serializer(template)
        return Response(
            {'message': 'Template archived successfully', 'data': serializer.data},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Restore an archived template.

        Restores template visibility in normal listings.
        """
        template = self.get_object()

        if not template.is_archived:
            return Response(
                {'error': 'Template is not archived'},
                status=status.HTTP_400_BAD_REQUEST
            )

        template.is_archived = False
        template.archived_at = None
        template.save()

        serializer = self.get_serializer(template)
        return Response(
            {'message': 'Template restored successfully', 'data': serializer.data},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Get all versions of this template.

        Returns version history with links to each version.
        """
        template = self.get_object()

        # Get all versions - current and previous versions
        versions = []

        # Get current template
        versions.append(template)

        # Get all previous versions
        current = template
        while current.previous_version:
            versions.append(current.previous_version)
            current = current.previous_version

        # Reverse to show oldest first
        versions.reverse()

        serializer = self.get_serializer(versions, many=True)
        return Response(
            {
                'count': len(versions),
                'current_version': template.version,
                'versions': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """
        Get all child templates inherited from this template.

        Returns list of templates that have this template as parent.
        """
        template = self.get_object()
        children = template.child_templates.filter(is_archived=False)

        serializer = self.get_serializer(children, many=True)
        return Response(
            {
                'count': children.count(),
                'parent_id': template.id,
                'children': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def validate_sections(self, request, pk=None):
        """
        Validate sections configuration.

        Request body:
        {
            "sections": [
                {
                    "name": "summary",
                    "fields": ["content", "date"]
                }
            ]
        }
        """
        template = self.get_object()
        sections = request.data.get('sections', template.sections)

        try:
            # Create a temporary template instance to validate
            temp_template = ReportTemplate(sections=sections)
            temp_template.validate_sections()

            return Response(
                {'message': 'Sections configuration is valid', 'sections': sections},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Validation failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def validate_layout(self, request, pk=None):
        """
        Validate layout configuration.

        Request body:
        {
            "layout_config": {
                "orientation": "portrait",
                "page_size": "a4",
                "margins": {
                    "top": 1.0,
                    "bottom": 1.0,
                    "left": 1.0,
                    "right": 1.0
                }
            }
        }
        """
        template = self.get_object()
        layout_config = request.data.get('layout_config', template.layout_config)

        try:
            # Create a temporary template instance to validate
            temp_template = ReportTemplate(layout_config=layout_config)
            temp_template.validate_layout_config()

            return Response(
                {'message': 'Layout configuration is valid', 'layout_config': layout_config},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Validation failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


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
    API ViewSet for managing report schedules.

    Endpoints:
    - GET /api/reports/schedules/ - List all schedules
    - POST /api/reports/schedules/ - Create new schedule
    - GET /api/reports/schedules/{id}/ - Get schedule details
    - PATCH /api/reports/schedules/{id}/ - Update schedule
    - DELETE /api/reports/schedules/{id}/ - Delete schedule
    - POST /api/reports/schedules/{id}/recipients/ - Add recipient
    - DELETE /api/reports/schedules/{id}/remove_recipient/ - Remove recipient
    - POST /api/reports/schedules/{id}/test_email/ - Send test email
    - GET /api/reports/schedules/{id}/executions/ - Get execution history
    - GET /api/reports/schedules/my_subscriptions/ - Get user's subscriptions
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_active', 'frequency']
    ordering_fields = ['next_scheduled', 'created_at']
    ordering = ['next_scheduled']

    def get_queryset(self):
        """Get schedules created by current user or user is recipient of."""
        user = self.request.user
        from reports.models import ReportScheduleRecipient

        # For create_by users, get their schedules
        if user.role in ['teacher', 'tutor', 'admin']:
            return ReportSchedule.objects.filter(
                created_by=user
            ).prefetch_related('recipient_entries')
        else:
            # For other users, get schedules they're subscribed to
            recipient_schedules = ReportScheduleRecipient.objects.filter(
                recipient=user, is_subscribed=True
            ).values_list('schedule_id', flat=True)
            return ReportSchedule.objects.filter(
                id__in=recipient_schedules, is_active=True
            ).prefetch_related('recipient_entries')

    def get_serializer_class(self):
        """Use detail serializer for retrieve, create/update for others."""
        if self.action == 'retrieve':
            from reports.serializers import ReportScheduleDetailSerializer
            return ReportScheduleDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            from reports.serializers import ReportScheduleCreateUpdateSerializer
            return ReportScheduleCreateUpdateSerializer
        return ReportScheduleSerializer

    def perform_create(self, serializer):
        """Set created_by to current user when creating schedule."""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def recipients(self, request, pk=None):
        """
        Add recipient to schedule.

        POST data:
        {
            "recipient_id": <user_id>
        }
        """
        from reports.models import ReportScheduleRecipient
        import secrets

        schedule = self.get_object()
        recipient_id = request.data.get('recipient_id')

        if not recipient_id:
            return Response(
                {'error': 'recipient_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            recipient = User.objects.get(id=recipient_id)

            # Create or update recipient
            recipient_entry, created = ReportScheduleRecipient.objects.get_or_create(
                schedule=schedule,
                recipient=recipient,
                defaults={
                    'unsubscribe_token': secrets.token_urlsafe(32),
                    'is_subscribed': True
                }
            )

            if not created and not recipient_entry.is_subscribed:
                recipient_entry.is_subscribed = True
                recipient_entry.unsubscribed_at = None
                recipient_entry.save()

            from reports.serializers import ReportScheduleRecipientSerializer
            serializer = ReportScheduleRecipientSerializer(recipient_entry)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response(
                {'error': 'Recipient not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['delete'])
    def remove_recipient(self, request, pk=None):
        """
        Remove recipient from schedule.

        DELETE: /api/reports/schedules/{id}/remove_recipient/?recipient_id=<user_id>
        """
        from reports.models import ReportScheduleRecipient

        schedule = self.get_object()
        recipient_id = request.query_params.get('recipient_id')

        if not recipient_id:
            return Response(
                {'error': 'recipient_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            recipient_entry = ReportScheduleRecipient.objects.get(
                schedule=schedule,
                recipient_id=recipient_id
            )
            recipient_entry.is_subscribed = False
            recipient_entry.unsubscribed_at = timezone.now()
            recipient_entry.save()

            return Response(
                {'message': 'Recipient unsubscribed successfully'},
                status=status.HTTP_200_OK
            )
        except ReportScheduleRecipient.DoesNotExist:
            return Response(
                {'error': 'Recipient not found in schedule'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def test_email(self, request, pk=None):
        """
        Send test email for schedule configuration.

        POST data:
        {
            "recipient_email": "test@example.com"
        }
        """
        from reports.tasks import test_email_report

        schedule = self.get_object()
        recipient_email = request.data.get('recipient_email')

        if not recipient_email:
            return Response(
                {'error': 'recipient_email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Send test email asynchronously
        task = test_email_report.delay(schedule.id, recipient_email)

        return Response(
            {
                'message': 'Test email queued for sending',
                'task_id': task.id,
                'recipient_email': recipient_email
            },
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """
        Get execution history for a schedule.

        Query params:
        - limit: Number of recent executions to return (default: 10)
        """
        from reports.serializers import ReportScheduleExecutionSerializer

        schedule = self.get_object()
        limit = int(request.query_params.get('limit', 10))

        executions = schedule.executions.all()[:limit]
        serializer = ReportScheduleExecutionSerializer(executions, many=True)

        return Response({
            'count': schedule.executions.count(),
            'results': serializer.data
        })

    @action(detail=False, methods=['get'])
    def my_subscriptions(self, request):
        """
        Get all schedules that the current user is subscribed to.

        Returns schedules where user is a recipient.
        """
        from reports.models import ReportScheduleRecipient

        subscriptions = ReportScheduleRecipient.objects.filter(
            recipient=request.user,
            is_subscribed=True
        ).select_related('schedule')

        schedules = [sub.schedule for sub in subscriptions]
        serializer = self.get_serializer(schedules, many=True)

        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def unsubscribe(self, request):
        """
        Unsubscribe from a report schedule using unsubscribe token.

        POST data:
        {
            "unsubscribe_token": "<token>"
        }

        This endpoint is used by email unsubscribe links.
        """
        from reports.models import ReportScheduleRecipient

        token = request.data.get('unsubscribe_token') or request.query_params.get('unsubscribe_token')

        if not token:
            return Response(
                {'error': 'unsubscribe_token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            recipient_entry = ReportScheduleRecipient.objects.get(
                unsubscribe_token=token
            )

            if recipient_entry.is_subscribed:
                recipient_entry.is_subscribed = False
                recipient_entry.unsubscribed_at = timezone.now()
                recipient_entry.save()

                return Response(
                    {
                        'message': 'Successfully unsubscribed from report schedule',
                        'schedule_name': recipient_entry.schedule.name or f'Schedule {recipient_entry.schedule.id}'
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'message': 'Already unsubscribed from this schedule'},
                    status=status.HTTP_200_OK
                )

        except ReportScheduleRecipient.DoesNotExist:
            return Response(
                {'error': 'Invalid unsubscribe token'},
                status=status.HTTP_404_NOT_FOUND
            )


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

    @action(detail=False, methods=['post'])
    def generate_now(self, request):
        """
        Generate weekly reports immediately for the teacher's students.

        Request body:
        {
            "week_start": "2024-01-01",  // optional, defaults to current week
            "student_id": 123,  // optional, specific student
            "subject_id": 456   // optional, specific subject
        }

        Returns:
            dict with generation results
        """
        if request.user.role != 'teacher':
            return Response(
                {'error': 'Only teachers can generate reports'},
                status=status.HTTP_403_FORBIDDEN
            )

        from datetime import date, timedelta
        from reports.services.teacher_weekly_report_service import TeacherWeeklyReportService

        try:
            # Parse request data
            week_start_str = request.data.get('week_start')
            student_id = request.data.get('student_id')
            subject_id = request.data.get('subject_id')

            # Determine week start date
            if week_start_str:
                try:
                    week_start = date.fromisoformat(week_start_str)
                except ValueError:
                    return Response(
                        {'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Default to Monday of current week
                today = timezone.now().date()
                week_start = today - timedelta(days=today.weekday())

            # Generate reports
            service = TeacherWeeklyReportService(request.user)
            report_data = service.generate_weekly_report(
                week_start=week_start,
                student_id=student_id,
                subject_id=subject_id,
                force_refresh=True
            )

            if 'error' in report_data:
                return Response(
                    {'error': report_data['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create records for generated reports
            created_reports = []
            for student_data in report_data.get('students', []):
                if 'error' not in student_data:
                    if subject_id:
                        created_report = service.create_weekly_report_record(
                            week_start=week_start,
                            student_id=student_data['student_id'],
                            subject_id=subject_id,
                            report_data=report_data
                        )

                        if created_report:
                            serializer = TeacherWeeklyReportSerializer(
                                created_report,
                                context={'request': request}
                            )
                            created_reports.append(serializer.data)

            return Response({
                'message': 'Reports generated successfully',
                'week_start': week_start.isoformat(),
                'reports_created': len(created_reports),
                'reports': created_reports,
                'summary': report_data.get('summary'),
                'statistics': report_data.get('statistics'),
                'recommendations': report_data.get('recommendations')
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error generating reports: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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