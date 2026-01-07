from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import (
    Notification,
    NotificationTemplate,
    NotificationSettings,
    NotificationQueue,
    NotificationClick,
)
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationCreateSerializer,
    NotificationTemplateSerializer,
    NotificationSettingsSerializer,
    NotificationQueueSerializer,
    NotificationStatsSerializer,
    BulkNotificationSerializer,
    NotificationMarkReadSerializer,
    ScheduleNotificationSerializer,
    ScheduleNotificationResponseSerializer,
    NotificationScheduleStatusSerializer,
    CancelScheduledNotificationSerializer,
    NotificationClickSerializer,
    TrackClickSerializer,
    NotificationAnalyticsSerializer,
    NotificationMetricsQuerySerializer,
)
from .analytics import NotificationAnalytics
from .services.template import TemplateService, TemplateSyntaxError, TemplateRenderError
from .scheduler import NotificationScheduler
from .unsubscribe import UnsubscribeTokenGenerator, UnsubscribeService
from .in_app_service import InAppNotificationService

User = get_user_model()


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet для уведомлений
    """

    queryset = Notification.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type", "priority", "is_read", "is_sent"]
    search_fields = ["title", "message"]
    ordering_fields = ["created_at", "read_at", "sent_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return NotificationListSerializer
        elif self.action == "create":
            return NotificationCreateSerializer
        return NotificationSerializer

    def get_queryset(self):
        """
        Пользователи видят только свои уведомления
        """
        return Notification.objects.filter(recipient=self.request.user)

    def perform_create(self, serializer):
        serializer.save(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        """
        Отметить уведомление как прочитанное
        """
        notification = self.get_object()
        notification.mark_as_read()
        return Response({"message": "Уведомление отмечено как прочитанное"})

    @action(detail=False, methods=["post"])
    def mark_multiple_read(self, request):
        """
        Отметить несколько уведомлений как прочитанные
        """
        serializer = NotificationMarkReadSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data["mark_all"]:
                # Отмечаем все уведомления пользователя как прочитанные
                updated_count = Notification.objects.filter(
                    recipient=request.user, is_read=False
                ).update(is_read=True, read_at=timezone.now())

                return Response(
                    {
                        "message": f"Отмечено как прочитанные: {updated_count} уведомлений"
                    }
                )
            else:
                # Отмечаем конкретные уведомления
                notification_ids = serializer.validated_data["notification_ids"]
                updated_count = Notification.objects.filter(
                    id__in=notification_ids, recipient=request.user, is_read=False
                ).update(is_read=True, read_at=timezone.now())

                return Response(
                    {
                        "message": f"Отмечено как прочитанные: {updated_count} уведомлений"
                    }
                )

        return Response(
            {"success": False, "error": "Ошибка валидации данных"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """
        Получить количество непрочитанных уведомлений
        """
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        return Response({"unread_count": count})

    @action(detail=False, methods=["post"])
    def send_bulk(self, request):
        """
        Отправить уведомления нескольким пользователям
        """
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            recipients = serializer.validated_data["recipients"]
            title = serializer.validated_data["title"]
            message = serializer.validated_data["message"]
            notification_type = serializer.validated_data["type"]
            priority = serializer.validated_data["priority"]
            data = serializer.validated_data.get("data", {})
            scheduled_at = serializer.validated_data.get("scheduled_at")

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
                        data=data,
                    )
                    notifications.append(notification)
                except User.DoesNotExist:
                    continue

            return Response(
                {
                    "message": f"Создано {len(notifications)} уведомлений",
                    "notifications": NotificationSerializer(
                        notifications, many=True
                    ).data,
                }
            )

        return Response(
            {"success": False, "error": "Ошибка валидации данных"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=False, methods=["get"])
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
            count = Notification.objects.filter(recipient=user, type=type_value).count()
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
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "sent_notifications": sent_notifications,
            "pending_notifications": 0,  # Заглушка
            "failed_notifications": 0,  # Заглушка
            "notifications_by_type": notifications_by_type,
            "notifications_by_priority": notifications_by_priority,
        }

        serializer = NotificationStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def schedule(self, request):
        """
        Schedule notifications for future delivery.

        POST /api/notifications/schedule/

        Body:
        {
            "recipients": [1, 2, 3],
            "title": "Scheduled Title",
            "message": "Scheduled message",
            "scheduled_at": "2025-12-28T10:00:00Z",
            "type": "system",
            "priority": "normal",
            "data": {}
        }

        Returns:
        {
            "notification_ids": [1, 2, 3],
            "count": 3,
            "scheduled_at": "2025-12-28T10:00:00Z"
        }
        """
        serializer = ScheduleNotificationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                scheduler = NotificationScheduler()
                created_ids = scheduler.schedule_notification(
                    recipients=serializer.validated_data["recipients"],
                    title=serializer.validated_data["title"],
                    message=serializer.validated_data["message"],
                    scheduled_at=serializer.validated_data["scheduled_at"],
                    notif_type=serializer.validated_data.get(
                        "type", Notification.Type.SYSTEM
                    ),
                    priority=serializer.validated_data.get(
                        "priority", Notification.Priority.NORMAL
                    ),
                    related_object_type=serializer.validated_data.get(
                        "related_object_type", ""
                    ),
                    related_object_id=serializer.validated_data.get(
                        "related_object_id"
                    ),
                    data=serializer.validated_data.get("data", {}),
                )

                response_serializer = ScheduleNotificationResponseSerializer(
                    {
                        "notification_ids": created_ids,
                        "count": len(created_ids),
                        "scheduled_at": serializer.validated_data["scheduled_at"],
                    }
                )
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response(
                    {"error": f"Scheduling failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(
            {"success": False, "error": "Ошибка валидации данных"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["delete"])
    def cancel_scheduled(self, request, pk=None):
        """
        Cancel a scheduled notification before it's sent.

        DELETE /api/notifications/{id}/cancel_scheduled/

        Returns:
        {
            "message": "Notification cancelled",
            "notification_id": 1
        }
        """
        notification = self.get_object()
        try:
            scheduler = NotificationScheduler()
            success = scheduler.cancel_scheduled(notification.id)

            if success:
                serializer = CancelScheduledNotificationSerializer(
                    {
                        "message": "Notification cancelled successfully",
                        "notification_id": notification.id,
                    }
                )
                return Response(serializer.data)
            else:
                return Response(
                    {"error": "Cannot cancel notification - not in pending state"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def schedule_status(self, request, pk=None):
        """
        Get the scheduling status of a notification.

        GET /api/notifications/{id}/schedule_status/

        Returns:
        {
            "id": 1,
            "title": "Scheduled Title",
            "scheduled_at": "2025-12-28T10:00:00Z",
            "scheduled_status": "pending",
            "is_sent": false,
            "sent_at": null,
            "created_at": "2025-12-27T10:00:00Z"
        }
        """
        notification = self.get_object()
        scheduler = NotificationScheduler()
        status_data = scheduler.get_schedule_status(notification.id)

        if status_data:
            serializer = NotificationScheduleStatusSerializer(status_data)
            return Response(serializer.data)
        else:
            return Response(
                {"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """
        Archive a notification (move to archive without deleting).

        POST /api/notifications/{id}/archive/

        Returns:
        {
            "message": "Notification archived successfully",
            "notification_id": 1
        }
        """
        notification = self.get_object()

        if InAppNotificationService.archive_notification(notification.id, request.user):
            return Response(
                {
                    "message": "Notification archived successfully",
                    "notification_id": notification.id,
                }
            )
        else:
            return Response(
                {"error": "Could not archive notification"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        """
        Restore an archived notification.

        POST /api/notifications/{id}/unarchive/

        Returns:
        {
            "message": "Notification unarchived successfully",
            "notification_id": 1
        }
        """
        notification = self.get_object()

        if InAppNotificationService.unarchive_notification(
            notification.id, request.user
        ):
            return Response(
                {
                    "message": "Notification unarchived successfully",
                    "notification_id": notification.id,
                }
            )
        else:
            return Response(
                {"error": "Could not unarchive notification"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, methods=["post"])
    def archive_multiple(self, request):
        """
        Archive multiple notifications at once.

        POST /api/notifications/archive_multiple/

        Body:
        {
            "notification_ids": [1, 2, 3]
        }

        Returns:
        {
            "message": "3 notifications archived",
            "count": 3
        }
        """
        notification_ids = request.data.get("notification_ids", [])

        if not notification_ids:
            return Response(
                {"error": "notification_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = Notification.objects.filter(
            id__in=notification_ids, recipient=request.user, is_archived=False
        ).update(is_archived=True, archived_at=timezone.now())

        return Response(
            {
                "message": f"{updated_count} notifications archived",
                "count": updated_count,
            }
        )

    @action(detail=False, methods=["post"])
    def delete_multiple(self, request):
        """
        Delete multiple notifications at once.

        POST /api/notifications/delete_multiple/

        Body:
        {
            "notification_ids": [1, 2, 3]
        }

        Returns:
        {
            "message": "3 notifications deleted",
            "count": 3
        }
        """
        notification_ids = request.data.get("notification_ids", [])

        if not notification_ids:
            return Response(
                {"error": "notification_ids is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count, _ = Notification.objects.filter(
            id__in=notification_ids, recipient=request.user
        ).delete()

        return Response(
            {
                "message": f"{deleted_count} notifications deleted",
                "count": deleted_count,
            }
        )

    @action(detail=False, methods=["get"])
    def archived(self, request):
        """
        Get archived notifications for the user.

        GET /api/notifications/archived/

        Query parameters:
        - limit: Number of notifications to return (default 50)
        - offset: Number of notifications to skip (default 0)

        Returns:
        {
            "count": 10,
            "results": [...]
        }
        """
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        archived_notifications = Notification.objects.filter(
            recipient=request.user, is_archived=True
        ).order_by("-archived_at")[offset : offset + limit]

        serializer = NotificationListSerializer(archived_notifications, many=True)

        return Response(
            {
                "count": Notification.objects.filter(
                    recipient=request.user, is_archived=True
                ).count(),
                "results": serializer.data,
            }
        )


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet для шаблонов уведомлений с функционалом предпросмотра, валидации и клонирования

    Доступные действия:
    - /api/notifications/templates/ - список и создание
    - /api/notifications/templates/{id}/ - получение, обновление, удаление
    - /api/notifications/templates/{id}/preview/ - предпросмотр шаблона
    - /api/notifications/templates/{id}/clone/ - клонирование шаблона
    - /api/notifications/templates/validate/ - валидация шаблона
    """

    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["type", "is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def preview(self, request, pk=None):
        """
        Предпросмотр шаблона с подставленными значениями

        POST /api/notifications/templates/{id}/preview/

        Body:
        {
            "context": {
                "user_name": "John Doe",
                "user_email": "john@example.com",
                "subject": "Mathematics",
                "date": "2025-12-27",
                "title": "Quiz 1",
                "grade": "95",
                "feedback": "Excellent work!"
            }
        }

        Returns:
        {
            "rendered_title": "New grade posted in Mathematics",
            "rendered_message": "You got 95 in Quiz 1"
        }
        """
        template = self.get_object()

        context = request.data.get("context", {})

        try:
            preview = TemplateService.preview(
                template.title_template, template.message_template, context
            )
            return Response(preview)
        except TemplateRenderError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAdminUser]
    )
    def validate(self, request):
        """
        Валидирует синтаксис шаблонов заголовка и сообщения

        POST /api/notifications/templates/validate/

        Body:
        {
            "title_template": "New grade in {{subject}}",
            "message_template": "You got {{grade}} in {{title}}"
        }

        Returns:
        {
            "is_valid": true,
            "errors": []
        }
        or
        {
            "is_valid": false,
            "errors": ["Title: unknown variable '{{unknown}}'"]
        }
        """
        title_template = request.data.get("title_template", "")
        message_template = request.data.get("message_template", "")

        is_valid, errors = TemplateService.validate(title_template, message_template)

        return Response({"is_valid": is_valid, "errors": errors})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def clone(self, request, pk=None):
        """
        Создает копию шаблона с суффиксом "_copy"

        POST /api/notifications/templates/{id}/clone/

        Returns:
        {
            "id": 2,
            "name": "Assignment Graded_copy",
            "description": "Шаблон уведомления о оценке задания",
            "type": "assignment_graded",
            "title_template": "Your assignment was graded",
            "message_template": "You got {{grade}} on {{title}}",
            "is_active": true,
            "created_at": "2025-12-27T10:00:00Z",
            "updated_at": "2025-12-27T10:00:00Z"
        }
        """
        template = self.get_object()

        # Создаем копию с новым именем
        new_name = f"{template.name}_copy"

        # Проверяем, что имя уникально
        copy_count = NotificationTemplate.objects.filter(
            name__startswith=f"{template.name}_copy"
        ).count()

        if copy_count > 0:
            new_name = f"{template.name}_copy_{copy_count + 1}"

        cloned_template = NotificationTemplate.objects.create(
            name=new_name,
            description=template.description,
            type=template.type,
            title_template=template.title_template,
            message_template=template.message_template,
            is_active=True,
        )

        serializer = self.get_serializer(cloned_template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
    filterset_fields = ["status", "channel"]
    ordering_fields = ["created_at", "scheduled_at", "processed_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        # Только администраторы могут видеть очередь
        if self.request.user.is_staff:
            return NotificationQueue.objects.all()
        return NotificationQueue.objects.none()


class AnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet для аналитики уведомлений

    Endpoints:
    - GET /api/notifications/analytics/metrics/ - Получить метрики доставки
    - GET /api/notifications/analytics/performance/ - Производительность каналов
    - GET /api/notifications/analytics/top-types/ - Топ типов по open rate
    """

    permission_classes = [permissions.IsAuthenticated]

    def _check_admin_permission(self, request):
        """
        Check if user has admin permission
        """
        if not request.user.is_staff:
            raise PermissionDenied(
                "Только администраторы могут просматривать аналитику"
            )

    @action(detail=False, methods=["get"])
    def metrics(self, request):
        """
        Get notification delivery metrics

        Query parameters:
        - date_from: Start date (YYYY-MM-DD), defaults to 7 days ago
        - date_to: End date (YYYY-MM-DD), defaults to today
        - type: Notification type filter (e.g., assignment_new)
        - channel: Delivery channel filter (email, push, sms, in_app)
        - granularity: Time grouping (hour, day, week), default: day
        - scope: Filter by scope (user, system, admin), default: all scopes
        """
        self._check_admin_permission(request)

        # Parse query parameters (convert empty strings to None)
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        notification_type = request.query_params.get("type") or None
        channel = request.query_params.get("channel") or None
        granularity = request.query_params.get("granularity", "day") or "day"
        scope = request.query_params.get("scope") or None

        # Build data dict for serializer (exclude None values)
        data = {
            "granularity": granularity,
        }
        if date_from is not None:
            data["date_from"] = date_from
        if date_to is not None:
            data["date_to"] = date_to
        if notification_type is not None:
            data["type"] = notification_type
        if channel is not None:
            data["channel"] = channel

        # Validate parameters
        serializer = NotificationMetricsQuerySerializer(data=data)

        if not serializer.is_valid():
            return Response(
                {"success": False, "error": "Ошибка валидации данных"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validated_data = serializer.validated_data

        try:
            # Get metrics from analytics service with optional scope filter
            # Pass None for optional filters that weren't provided
            metrics = NotificationAnalytics.get_metrics(
                date_from=validated_data.get("date_from"),
                date_to=validated_data.get("date_to"),
                notification_type=validated_data.get("type"),
                channel=validated_data.get("channel"),
                granularity=validated_data.get("granularity", "day"),
                scope=scope,  # Pass scope parameter
            )

            # Serialize response
            response_serializer = NotificationAnalyticsSerializer(metrics)
            return Response(response_serializer.data)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def performance(self, request):
        """
        Get channel performance metrics
        """
        self._check_admin_permission(request)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        try:
            channel_perf = NotificationAnalytics.get_channel_performance(
                date_from=date_from,
                date_to=date_to,
            )

            # Format response
            channels = [
                {"channel": channel, **metrics}
                for channel, metrics in channel_perf.items()
            ]

            # Find best and worst channels
            best_channel = max(
                channels, key=lambda x: x.get("delivery_rate", 0), default=None
            )
            worst_channel = min(
                channels, key=lambda x: x.get("delivery_rate", 0), default=None
            )

            return Response(
                {
                    "channels": channels,
                    "best_channel": best_channel,
                    "worst_channel": worst_channel,
                }
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def top_types(self, request):
        """
        Get top performing notification types by open rate
        """
        self._check_admin_permission(request)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        limit = int(request.query_params.get("limit", 5))

        try:
            top_types = NotificationAnalytics.get_top_performing_types(
                date_from=date_from,
                date_to=date_to,
                limit=limit,
            )

            return Response(
                {
                    "top_types": top_types,
                }
            )

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def track_click(self, request):
        """
        Track a click on a notification.

        POST /api/notifications/analytics/track_click/

        Body:
        {
            "notification_id": 123,
            "action_type": "link_click",
            "action_url": "https://example.com/path",
            "action_data": {"key": "value"},
            "user_agent": "Mozilla/5.0...",
            "ip_address": "192.168.1.1"
        }

        Returns:
        {
            "id": 1,
            "notification_id": 123,
            "notification_title": "Example notification",
            "user": 456,
            "user_email": "user@example.com",
            "action_type": "link_click",
            "action_url": "https://example.com/path",
            "created_at": "2025-12-27T12:00:00Z"
        }
        """
        serializer = TrackClickSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        try:
            # Get client IP if not provided
            ip_address = validated_data.get("ip_address")
            if not ip_address:
                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if x_forwarded_for:
                    ip_address = x_forwarded_for.split(",")[0]
                else:
                    ip_address = request.META.get("REMOTE_ADDR")

            # Get user agent if not provided
            user_agent = validated_data.get("user_agent") or request.META.get(
                "HTTP_USER_AGENT", ""
            )

            # Track the click
            click = NotificationAnalytics.track_click(
                notification_id=validated_data["notification_id"],
                user_id=request.user.id,
                action_type=validated_data.get("action_type", "link_click"),
                action_url=validated_data.get("action_url"),
                action_data=validated_data.get("action_data"),
                user_agent=user_agent,
                ip_address=ip_address,
            )

            if click is None:
                return Response(
                    {"error": "Notification not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response_serializer = NotificationClickSerializer(click)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UnsubscribeView(APIView):
    """
    Secure one-click unsubscribe endpoint.

    GET /api/notifications/unsubscribe/{token}/
    Query params:
    - type: Notification type(s) to unsubscribe from (default: 'all')
             Examples: 'assignments', 'materials', 'messages', 'all'

    Validates HMAC-SHA256 token signature and expiry (30 days).
    Updates NotificationSettings for the user.

    Success Response (200):
    {
        "success": true,
        "message": "Successfully unsubscribed from: assignments, materials",
        "disabled_types": ["assignments", "materials"],
        "user_id": 123,
        "user_email": "user@example.com"
    }

    Error Response (400):
    {
        "success": false,
        "error": "Invalid token" | "Expired token" | "User not found",
        "message": "Detailed error message"
    }
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        """
        Process unsubscribe request.

        Args:
            request: HTTP request
            token: HMAC-signed unsubscribe token

        Returns:
            JSON response with status
        """
        # Get notification type(s) from query params
        notif_type = request.query_params.get("type", "all")
        notification_types = [t.strip() for t in notif_type.split(",") if t.strip()]

        # Validate token
        is_valid, token_data = UnsubscribeTokenGenerator.validate(token)

        if not is_valid:
            return Response(
                {
                    "success": False,
                    "error": "Invalid or expired token",
                    "message": "The unsubscribe link is invalid or has expired. "
                    "Please try again or contact support.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract user_id from token
        user_id = token_data.get("user_id")
        token_types = token_data.get("notification_types", [])

        # Determine which types to disable
        # Priority: token_types (from URL) > query param > 'all'
        if token_types and token_types != ["all"]:
            types_to_disable = token_types
        elif notification_types and notification_types != ["all"]:
            types_to_disable = notification_types
        else:
            types_to_disable = ["all"]

        # Extract client information for audit trail
        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        # Process unsubscribe
        result = UnsubscribeService.unsubscribe(
            user_id,
            types_to_disable,
            ip_address=ip_address,
            user_agent=user_agent,
            token_used=True,
        )

        if not result.get("success"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
