from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Material, MaterialProgress, Subject
from chat.models import ChatRoom, Message

User = get_user_model()


class StudentInfoSerializer(serializers.Serializer):
    """
    Сериализатор для информации о студенте
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    avatar = serializers.URLField(read_only=True, allow_null=True)


class SubjectInfoSerializer(serializers.ModelSerializer):
    """
    Сериализатор для информации о предмете
    """
    class Meta:
        model = Subject
        fields = ('id', 'name', 'color')


class AuthorInfoSerializer(serializers.Serializer):
    """
    Сериализатор для информации об авторе
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)


class MaterialProgressSerializer(serializers.Serializer):
    """
    Сериализатор для прогресса изучения материала
    """
    is_completed = serializers.BooleanField()
    progress_percentage = serializers.IntegerField()
    time_spent = serializers.IntegerField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    last_accessed = serializers.DateTimeField(allow_null=True)


class StudentMaterialSerializer(serializers.Serializer):
    """
    Сериализатор для материала в контексте студента
    """
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    type = serializers.CharField(read_only=True)
    difficulty_level = serializers.IntegerField(read_only=True)
    subject = SubjectInfoSerializer(read_only=True)
    author = AuthorInfoSerializer(read_only=True)
    file_url = serializers.URLField(read_only=True, allow_null=True)
    video_url = serializers.URLField(read_only=True, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )
    created_at = serializers.DateTimeField(read_only=True)
    published_at = serializers.DateTimeField(read_only=True, allow_null=True)
    progress = MaterialProgressSerializer(read_only=True)


class SubjectMaterialsSerializer(serializers.Serializer):
    """
    Сериализатор для материалов, сгруппированных по предметам
    """
    subject_info = SubjectInfoSerializer(read_only=True)
    materials = StudentMaterialSerializer(many=True, read_only=True)


class SubjectStatisticsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики по предмету
    """
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    not_started = serializers.IntegerField()


class ProgressStatisticsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики прогресса студента
    """
    total_materials = serializers.IntegerField()
    completed_materials = serializers.IntegerField()
    in_progress_materials = serializers.IntegerField()
    not_started_materials = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    average_progress = serializers.FloatField()
    total_time_spent = serializers.IntegerField()
    subject_statistics = serializers.DictField(
        child=SubjectStatisticsSerializer()
    )


class ActivityDataSerializer(serializers.Serializer):
    """
    Сериализатор для данных активности
    """
    material_id = serializers.IntegerField(read_only=True)
    subject_id = serializers.IntegerField(read_only=True)
    progress_percentage = serializers.IntegerField(read_only=True)
    time_spent = serializers.IntegerField(read_only=True, required=False)


class RecentActivitySerializer(serializers.Serializer):
    """
    Сериализатор для недавней активности
    """
    type = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)
    data = ActivityDataSerializer(read_only=True)


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для сообщений чата
    """
    sender = AuthorInfoSerializer(read_only=True)
    
    class Meta:
        model = Message
        fields = (
            'id', 'content', 'sender', 'message_type',
            'created_at', 'is_edited'
        )


class GeneralChatSerializer(serializers.Serializer):
    """
    Сериализатор для общего чата
    """
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    is_participant = serializers.BooleanField(read_only=True)
    participants_count = serializers.IntegerField(read_only=True)
    recent_messages = ChatMessageSerializer(many=True, read_only=True)


class StudentDashboardSerializer(serializers.Serializer):
    """
    Сериализатор для полных данных дашборда студента
    """
    student_info = StudentInfoSerializer(read_only=True)
    materials_by_subject = serializers.DictField(
        child=SubjectMaterialsSerializer()
    )
    progress_statistics = ProgressStatisticsSerializer(read_only=True)
    recent_activity = RecentActivitySerializer(many=True, read_only=True)
    general_chat = GeneralChatSerializer(read_only=True, allow_null=True)


class MaterialProgressUpdateSerializer(serializers.Serializer):
    """
    Сериализатор для обновления прогресса материала
    """
    progress_percentage = serializers.IntegerField(
        min_value=0,
        max_value=100,
        help_text="Процент выполнения от 0 до 100"
    )
    time_spent = serializers.IntegerField(
        min_value=0,
        help_text="Время, потраченное на изучение в минутах"
    )
    
    def validate_progress_percentage(self, value):
        """
        Валидация процента прогресса
        """
        if not isinstance(value, (int, float)):
            raise serializers.ValidationError("Процент прогресса должен быть числом")
        return int(value)
    
    def validate_time_spent(self, value):
        """
        Валидация времени изучения
        """
        if not isinstance(value, (int, float)):
            raise serializers.ValidationError("Время изучения должно быть числом")
        return int(value)
