from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone

from .models import Notification, NotificationTemplate, NotificationSettings, NotificationQueue
from .serializers import (
    NotificationSerializer, NotificationListSerializer, NotificationCreateSerializer,
    NotificationTemplateSerializer, NotificationSettingsSerializer, NotificationQueueSerializer,
    NotificationStatsSerializer, BulkNotificationSerializer, NotificationMarkReadSerializer
)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для уведомлений
    """
    queryset = Notification.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'priority', 'is_read', 'is_sent']
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'read_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        elif self.action == 'create':
            return NotificationCreateSerializer
        return NotificationSerializer
    
    def get_queryset(self):
        """
        Пользователи видят только свои уведомления
        """
        return Notification.objects.filter(recipient=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Отметить уведомление как прочитанное
        """
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'message': 'Уведомление отмечено как прочитанное'})
    
    @action(detail=False, methods=['post'])
    def mark_multiple_read(self, request):
        """
        Отметить несколько уведомлений как прочитанные
        """
        serializer = NotificationMarkReadSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['mark_all']:
                # Отмечаем все уведомления пользователя как прочитанные
                updated_count = Notification.objects.filter(
                    recipient=request.user,
                    is_read=False
                ).update(is_read=True, read_at=timezone.now())
                
                return Response({
                    'message': f'Отмечено как прочитанные: {updated_count} уведомлений'
                })
            else:
                # Отмечаем конкретные уведомления
                notification_ids = serializer.validated_data['notification_ids']
                updated_count = Notification.objects.filter(
                    id__in=notification_ids,
                    recipient=request.user,
                    is_read=False
                ).update(is_read=True, read_at=timezone.now())
                
                return Response({
                    'message': f'Отмечено как прочитанные: {updated_count} уведомлений'
                })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Получить количество непрочитанных уведомлений
        """
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['post'])
    def send_bulk(self, request):
        """
        Отправить уведомления нескольким пользователям
        """
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            recipients = serializer.validated_data['recipients']
            title = serializer.validated_data['title']
            message = serializer.validated_data['message']
            notification_type = serializer.validated_data['type']
            priority = serializer.validated_data['priority']
            data = serializer.validated_data.get('data', {})
            scheduled_at = serializer.validated_data.get('scheduled_at')
            
            # Создаем уведомления для каждого получателя
            notifications = []
            for recipient_id in recipients:
                try:
                    recipient = User.objects.get(id=recipient_id)
                    notification = Notification.objects.create(
                        recipient=recipient,
                        title=title,
                        message=message,
                        type=notification_type,
                        priority=priority,
                        data=data
                    )
                    notifications.append(notification)
                except User.DoesNotExist:
                    continue
            
            return Response({
                'message': f'Создано {len(notifications)} уведомлений',
                'notifications': NotificationSerializer(notifications, many=True).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Получить статистику уведомлений
        """
        user = request.user
        
        # Общая статистика
        total_notifications = Notification.objects.filter(recipient=user).count()
        unread_notifications = Notification.objects.filter(
            recipient=user, is_read=False
        ).count()
        sent_notifications = Notification.objects.filter(
            recipient=user, is_sent=True
        ).count()
        
        # Статистика по типам
        notifications_by_type = {}
        for type_choice in Notification.Type.choices:
            type_value = type_choice[0]
            count = Notification.objects.filter(
                recipient=user, type=type_value
            ).count()
            notifications_by_type[type_value] = count
        
        # Статистика по приоритетам
        notifications_by_priority = {}
        for priority_choice in Notification.Priority.choices:
            priority_value = priority_choice[0]
            count = Notification.objects.filter(
                recipient=user, priority=priority_value
            ).count()
            notifications_by_priority[priority_value] = count
        
        stats_data = {
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'sent_notifications': sent_notifications,
            'pending_notifications': 0,  # Заглушка
            'failed_notifications': 0,   # Заглушка
            'notifications_by_type': notifications_by_type,
            'notifications_by_priority': notifications_by_priority
        }
        
        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet для шаблонов уведомлений
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']


class NotificationSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet для настроек уведомлений
    """
    queryset = NotificationSettings.objects.all()
    serializer_class = NotificationSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return NotificationSettings.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NotificationQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для очереди уведомлений (только для администраторов)
    """
    queryset = NotificationQueue.objects.all()
    serializer_class = NotificationQueueSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'channel']
    ordering_fields = ['created_at', 'scheduled_at', 'processed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        # Только администраторы могут видеть очередь
        if self.request.user.is_staff:
            return NotificationQueue.objects.all()
        return NotificationQueue.objects.none()