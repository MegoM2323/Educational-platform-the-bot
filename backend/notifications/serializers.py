from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Notification, NotificationTemplate, NotificationSettings, NotificationQueue,
    NotificationClick, NotificationUnsubscribe
)

User = get_user_model()


class NotificationSerializer(serializers.ModelSerializer):
    """
    Сериализатор для уведомлений
    """
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'message', 'recipient', 'recipient_name', 'type',
            'type_display', 'priority', 'priority_display', 'is_read', 'is_sent',
            'related_object_type', 'related_object_id', 'data', 'created_at',
            'read_at', 'sent_at'
        )
        read_only_fields = ('id', 'created_at', 'read_at', 'sent_at')
    
    def create(self, validated_data):
        validated_data['recipient'] = self.context['request'].user
        return super().create(validated_data)


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка уведомлений
    """
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'message', 'type', 'type_display', 'priority',
            'priority_display', 'is_read', 'is_sent', 'created_at', 'read_at'
        )


class NotificationCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания уведомления
    """
    class Meta:
        model = Notification
        fields = (
            'title', 'message', 'recipient', 'type', 'priority',
            'related_object_type', 'related_object_id', 'data'
        )


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для шаблонов уведомлений
    """
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = (
            'id', 'name', 'description', 'type', 'type_display',
            'title_template', 'message_template', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class NotificationSettingsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для настроек уведомлений
    """
    timezone_display = serializers.CharField(source='get_timezone_display', read_only=True)

    class Meta:
        model = NotificationSettings
        fields = (
            'id', 'user', 'assignment_notifications', 'material_notifications',
            'message_notifications', 'report_notifications', 'payment_notifications',
            'invoice_notifications', 'system_notifications', 'email_notifications',
            'push_notifications', 'sms_notifications', 'in_app_notifications',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'timezone', 'timezone_display', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'timezone_display', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class NotificationQueueSerializer(serializers.ModelSerializer):
    """
    Сериализатор для очереди уведомлений
    """
    notification_title = serializers.CharField(source='notification.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    
    class Meta:
        model = NotificationQueue
        fields = (
            'id', 'notification', 'notification_title', 'status', 'status_display',
            'channel', 'channel_display', 'scheduled_at', 'attempts', 'max_attempts',
            'error_message', 'created_at', 'processed_at'
        )
        read_only_fields = ('id', 'created_at', 'processed_at')


class NotificationStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики уведомлений
    """
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    pending_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    notifications_by_type = serializers.DictField()
    notifications_by_priority = serializers.DictField()


class BulkNotificationSerializer(serializers.Serializer):
    """
    Сериализатор для массовой отправки уведомлений
    """
    recipients = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Список ID получателей'
    )
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    type = serializers.ChoiceField(choices=Notification.Type.choices)
    priority = serializers.ChoiceField(
        choices=Notification.Priority.choices,
        default=Notification.Priority.NORMAL
    )
    data = serializers.JSONField(required=False, default=dict)
    scheduled_at = serializers.DateTimeField(required=False)


class NotificationMarkReadSerializer(serializers.Serializer):
    """
    Сериализатор для отметки уведомлений как прочитанных
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Список ID уведомлений для отметки как прочитанных'
    )
    mark_all = serializers.BooleanField(
        default=False,
        help_text='Отметить все уведомления как прочитанные'
    )


# ============= BROADCAST SERIALIZERS =============

class BroadcastRecipientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получателей рассылки с информацией о доставке
    """
    user_id = serializers.IntegerField(source='recipient.id', read_only=True)
    user_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    email = serializers.CharField(source='recipient.email', read_only=True)
    telegram_id = serializers.SerializerMethodField()
    error_message = serializers.CharField(source='telegram_error', read_only=True)

    class Meta:
        from .models import BroadcastRecipient
        model = BroadcastRecipient
        fields = [
            'id', 'user_id', 'user_name', 'email', 'telegram_id',
            'telegram_sent', 'error_message', 'sent_at'
        ]
        read_only_fields = ['id', 'sent_at']

    def get_telegram_id(self, obj):
        """Получить telegram_id пользователя в зависимости от роли"""
        user = obj.recipient
        telegram_id = None

        try:
            if user.role == 'student' and hasattr(user, 'student_profile'):
                telegram_id = user.student_profile.telegram_id
            elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
                telegram_id = user.teacher_profile.telegram_id
            elif user.role == 'tutor' and hasattr(user, 'tutor_profile'):
                telegram_id = user.tutor_profile.telegram_id
            elif user.role == 'parent' and hasattr(user, 'parent_profile'):
                telegram_id = user.parent_profile.telegram_id
        except Exception:
            return None

        return telegram_id


class BroadcastListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка рассылок (без полного списка получателей)
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    target_group_display = serializers.CharField(source='get_target_group_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        from .models import Broadcast
        model = Broadcast
        fields = [
            'id', 'created_by', 'created_by_name', 'target_group', 'target_group_display',
            'message', 'status', 'status_display', 'recipient_count', 'sent_count', 'failed_count',
            'scheduled_at', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'recipient_count', 'sent_count', 'failed_count', 'sent_at', 'created_at']


class BroadcastDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о рассылке (включает получателей)
    """
    from accounts.serializers import UserMinimalSerializer
    created_by = UserMinimalSerializer(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    target_group_display = serializers.CharField(source='get_target_group_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recipients = BroadcastRecipientSerializer(many=True, read_only=True)

    class Meta:
        from .models import Broadcast
        model = Broadcast
        fields = [
            'id', 'created_by', 'created_by_name', 'target_group', 'target_group_display',
            'target_filter', 'message', 'status', 'status_display', 'recipient_count',
            'sent_count', 'failed_count', 'recipients', 'scheduled_at', 'sent_at', 'created_at'
        ]
        read_only_fields = ['id', 'recipient_count', 'sent_count', 'failed_count', 'sent_at', 'created_at']


class CreateBroadcastSerializer(serializers.Serializer):
    """
    Сериализатор для создания новой рассылки
    """
    target_group = serializers.ChoiceField(
        choices=['all_students', 'all_teachers', 'all_tutors', 'all_parents', 'by_subject', 'by_tutor', 'by_teacher', 'custom']
    )
    target_filter = serializers.JSONField(
        required=False,
        allow_null=True,
        help_text='Фильтры: subject_id, tutor_id, teacher_id, user_ids'
    )
    message = serializers.CharField(max_length=4000)
    send_telegram = serializers.BooleanField(default=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


# ============= ANALYTICS SERIALIZERS =============

class NotificationMetricsQuerySerializer(serializers.Serializer):
    """
    Сериализатор для параметров запроса аналитики
    """
    date_from = serializers.DateField(
        required=False,
        allow_null=True,
        help_text='Start date (YYYY-MM-DD), defaults to 7 days ago'
    )
    date_to = serializers.DateField(
        required=False,
        allow_null=True,
        help_text='End date (YYYY-MM-DD), defaults to today'
    )
    type = serializers.ChoiceField(
        choices=[choice[0] for choice in Notification.Type.choices],
        required=False,
        allow_null=True,
        help_text='Filter by notification type'
    )
    channel = serializers.ChoiceField(
        choices=['email', 'push', 'sms', 'in_app'],
        required=False,
        allow_null=True,
        help_text='Filter by delivery channel'
    )
    granularity = serializers.ChoiceField(
        choices=['hour', 'day', 'week'],
        default='day',
        required=False,
        help_text='Time grouping for metrics'
    )


class ChannelMetricsSerializer(serializers.Serializer):
    """
    Сериализатор для метрик по каналам
    """
    count = serializers.IntegerField()
    delivered = serializers.IntegerField()
    failed = serializers.IntegerField()
    delivery_rate = serializers.FloatField()


class TypeMetricsSerializer(serializers.Serializer):
    """
    Сериализатор для метрик по типам уведомлений
    """
    count = serializers.IntegerField()
    delivered = serializers.IntegerField()
    opened = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()


class TimeMetricsItemSerializer(serializers.Serializer):
    """
    Сериализатор для временных метрик
    """
    time = serializers.CharField()
    count = serializers.IntegerField()
    sent = serializers.IntegerField()
    opened = serializers.IntegerField()


class SummaryMetricsSerializer(serializers.Serializer):
    """
    Сериализатор для итоговой статистики
    """
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_opened = serializers.IntegerField()
    total_failed = serializers.IntegerField()
    avg_delivery_time = serializers.CharField()
    failures = serializers.IntegerField()
    error_reasons = serializers.ListField(child=serializers.CharField())


class NotificationAnalyticsSerializer(serializers.Serializer):
    """
    Сериализатор для полной аналитики уведомлений
    """
    date_from = serializers.DateTimeField()
    date_to = serializers.DateTimeField()
    total_sent = serializers.IntegerField()
    total_delivered = serializers.IntegerField()
    total_opened = serializers.IntegerField()
    delivery_rate = serializers.FloatField()
    open_rate = serializers.FloatField()
    by_type = serializers.DictField(child=TypeMetricsSerializer())
    by_channel = serializers.DictField(child=ChannelMetricsSerializer())
    by_time = TimeMetricsItemSerializer(many=True)
    summary = SummaryMetricsSerializer()


class ChannelPerformanceSerializer(serializers.Serializer):
    """
    Сериализатор для производительности каналов
    """
    channel = serializers.CharField()
    count = serializers.IntegerField()
    delivered = serializers.IntegerField()
    failed = serializers.IntegerField()
    delivery_rate = serializers.FloatField()


class TopNotificationTypesSerializer(serializers.Serializer):
    """
    Сериализатор для топ типов уведомлений
    """
    type = serializers.CharField()
    open_rate = serializers.FloatField()
    count = serializers.IntegerField()


# ============= SCHEDULING SERIALIZERS =============

class ScheduleNotificationSerializer(serializers.Serializer):
    """
    Сериализатор для создания запланированного уведомления
    """
    recipients = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of user IDs to receive the notification'
    )
    title = serializers.CharField(
        max_length=200,
        help_text='Notification title'
    )
    message = serializers.CharField(
        help_text='Notification message'
    )
    scheduled_at = serializers.DateTimeField(
        help_text='When to send (ISO format, must be in future)'
    )
    type = serializers.ChoiceField(
        choices=Notification.Type.choices,
        default=Notification.Type.SYSTEM,
        help_text='Notification type'
    )
    priority = serializers.ChoiceField(
        choices=Notification.Priority.choices,
        default=Notification.Priority.NORMAL,
        help_text='Priority level'
    )
    related_object_type = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text='Type of related object'
    )
    related_object_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='ID of related object'
    )
    data = serializers.JSONField(
        required=False,
        default=dict,
        help_text='Additional data'
    )


class ScheduleNotificationResponseSerializer(serializers.Serializer):
    """
    Сериализатор для ответа при создании запланированного уведомления
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='Created notification IDs'
    )
    count = serializers.IntegerField(
        help_text='Number of notifications created'
    )
    scheduled_at = serializers.DateTimeField(
        help_text='Scheduled send time'
    )


class NotificationScheduleStatusSerializer(serializers.Serializer):
    """
    Сериализатор для статуса запланированного уведомления
    """
    id = serializers.IntegerField()
    title = serializers.CharField()
    scheduled_at = serializers.DateTimeField()
    scheduled_status = serializers.CharField()
    is_sent = serializers.BooleanField()
    sent_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class CancelScheduledNotificationSerializer(serializers.Serializer):
    """
    Сериализатор для отмены запланированного уведомления
    """
    message = serializers.CharField(
        help_text='Cancellation confirmation message'
    )
    notification_id = serializers.IntegerField()


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка уведомлений с информацией о расписании
    """
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id', 'title', 'message', 'type', 'type_display', 'priority',
            'priority_display', 'is_read', 'is_sent', 'created_at', 'read_at',
            'scheduled_at', 'scheduled_status'
        )


class NotificationClickSerializer(serializers.ModelSerializer):
    """
    Serializer for tracking notification clicks
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    notification_title = serializers.CharField(source='notification.title', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)

    class Meta:
        model = NotificationClick
        fields = (
            'id', 'notification', 'notification_title', 'user', 'user_email',
            'action_type', 'action_type_display', 'action_url', 'action_data',
            'user_agent', 'ip_address', 'created_at'
        )
        read_only_fields = (
            'id', 'notification', 'user', 'user_email', 'notification_title',
            'action_type_display', 'created_at'
        )


class TrackClickSerializer(serializers.Serializer):
    """
    Serializer for tracking a click on a notification
    """
    notification_id = serializers.IntegerField(required=True)
    action_type = serializers.ChoiceField(
        choices=[
            ('link_click', 'Link Click'),
            ('in_app_click', 'In-App Click'),
            ('email_click', 'Email Click'),
            ('button_click', 'Button Click'),
        ],
        default='link_click'
    )
    action_url = serializers.URLField(required=False, allow_blank=True)
    action_data = serializers.JSONField(required=False)
    user_agent = serializers.CharField(required=False, allow_blank=True)
    ip_address = serializers.IPAddressField(required=False, allow_blank=True)


class NotificationUnsubscribeSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationUnsubscribe model (GDPR compliance).
    Tracks unsubscribe history for audit purposes.
    """
    user_email = serializers.CharField(source='user.email', read_only=True)
    is_active = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationUnsubscribe
        fields = (
            'id', 'user', 'user_email', 'notification_types', 'channel',
            'token_used', 'reason', 'ip_address', 'user_agent',
            'unsubscribed_at', 'resubscribed_at', 'is_active'
        )
        read_only_fields = (
            'id', 'user', 'unsubscribed_at', 'ip_address', 'user_agent'
        )
    
    def get_is_active(self, obj):
        """Check if unsubscribe is still active (not resubscribed)"""
        return obj.is_active()
