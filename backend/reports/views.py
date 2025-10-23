from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Report, ReportTemplate, ReportRecipient, AnalyticsData, ReportSchedule
from .serializers import (
    ReportListSerializer, ReportDetailSerializer, ReportCreateSerializer,
    ReportTemplateSerializer, ReportRecipientSerializer, AnalyticsDataSerializer,
    ReportScheduleSerializer, ReportStatsSerializer, StudentProgressSerializer,
    ClassPerformanceSerializer
)


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