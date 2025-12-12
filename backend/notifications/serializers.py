from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Notification, NotificationTemplate, NotificationSettings, NotificationQueue

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
    class Meta:
        model = NotificationSettings
        fields = (
            'id', 'user', 'assignment_notifications', 'material_notifications',
            'message_notifications', 'report_notifications', 'payment_notifications',
            'system_notifications', 'email_notifications', 'push_notifications',
            'sms_notifications', 'quiet_hours_start', 'quiet_hours_end',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')
    
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
