from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Material, MaterialProgress, Subject
from reports.models import Report, ReportRecipient

User = get_user_model()


class SubjectSerializer(serializers.ModelSerializer):
    """Сериализатор для предметов"""
    
    class Meta:
        model = Subject
        fields = ['id', 'name', 'description', 'color']


class StudentProfileSerializer(serializers.Serializer):
    """Сериализатор для профиля студента"""
    grade = serializers.CharField()
    goal = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    total_points = serializers.IntegerField()
    accuracy_percentage = serializers.IntegerField()


class StudentSerializer(serializers.Serializer):
    """Сериализатор для студентов в дашборде учителя"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.URLField(allow_null=True)
    profile = StudentProfileSerializer()
    assigned_materials_count = serializers.IntegerField()
    completed_materials_count = serializers.IntegerField()
    completion_percentage = serializers.FloatField()


class MaterialSerializer(serializers.ModelSerializer):
    """Сериализатор для материалов в дашборде учителя"""
    subject = SubjectSerializer(read_only=True)
    assigned_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
    average_progress = serializers.FloatField(read_only=True)
    file_url = serializers.URLField(source='file.url', read_only=True, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), read_only=True)
    
    class Meta:
        model = Material
        fields = [
            'id', 'title', 'description', 'type', 'status', 'difficulty_level',
            'subject', 'file_url', 'video_url', 'tags', 'created_at', 'published_at',
            'assigned_count', 'completed_count', 'completion_percentage', 'average_progress'
        ]


class ProgressOverviewSerializer(serializers.Serializer):
    """Сериализатор для обзора прогресса"""
    total_students = serializers.IntegerField(required=False)
    total_materials = serializers.IntegerField(required=False)
    total_assignments = serializers.IntegerField(required=False)
    completed_assignments = serializers.IntegerField(required=False)
    completion_percentage = serializers.FloatField(required=False)
    average_progress = serializers.FloatField(required=False)
    subject_statistics = serializers.DictField(required=False)
    
    # Поля для детального обзора студента
    student = serializers.DictField(required=False)
    subject_progress = serializers.DictField(required=False)
    total_materials = serializers.IntegerField(required=False)
    completed_materials = serializers.IntegerField(required=False)
    overall_completion_percentage = serializers.FloatField(required=False)


class ReportSerializer(serializers.ModelSerializer):
    """Сериализатор для отчетов"""
    target_students_count = serializers.IntegerField(read_only=True)
    target_parents_count = serializers.IntegerField(read_only=True)
    total_recipients = serializers.IntegerField(read_only=True)
    sent_recipients = serializers.IntegerField(read_only=True)
    delivery_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Report
        fields = [
            'id', 'title', 'description', 'type', 'status', 'start_date', 'end_date',
            'created_at', 'sent_at', 'target_students_count', 'target_parents_count',
            'total_recipients', 'sent_recipients', 'delivery_percentage'
        ]


class ChatMessageSerializer(serializers.Serializer):
    """Сериализатор для сообщений чата"""
    id = serializers.IntegerField()
    content = serializers.CharField()
    sender = serializers.DictField()
    message_type = serializers.CharField()
    created_at = serializers.DateTimeField()
    is_edited = serializers.BooleanField()


class GeneralChatSerializer(serializers.Serializer):
    """Сериализатор для общего чата"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    is_participant = serializers.BooleanField()
    participants_count = serializers.IntegerField()
    recent_messages = ChatMessageSerializer(many=True)


class TeacherDashboardSerializer(serializers.Serializer):
    """Сериализатор для полного дашборда учителя"""
    teacher_info = serializers.DictField()
    students = StudentSerializer(many=True)
    materials = MaterialSerializer(many=True)
    progress_overview = ProgressOverviewSerializer()
    reports = ReportSerializer(many=True)
    general_chat = GeneralChatSerializer(allow_null=True)


class DistributeMaterialSerializer(serializers.Serializer):
    """Сериализатор для распределения материалов"""
    material_id = serializers.IntegerField()
    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    
    def validate_material_id(self, value):
        """Проверяем, что материал существует и принадлежит учителю"""
        try:
            material = Material.objects.get(id=value)
            if material.author != self.context['request'].user:
                raise serializers.ValidationError(
                    "У вас нет прав на редактирование этого материала"
                )
            return value
        except Material.DoesNotExist:
            raise serializers.ValidationError("Материал не найден")
    
    def validate_student_ids(self, value):
        """Проверяем, что все студенты существуют"""
        students = User.objects.filter(id__in=value, role=User.Role.STUDENT)
        if len(students) != len(value):
            raise serializers.ValidationError(
                "Некоторые студенты не найдены или имеют неправильную роль"
            )
        return value


class CreateReportSerializer(serializers.Serializer):
    """Сериализатор для создания отчета"""
    student_id = serializers.IntegerField()
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=Report.Type.choices, required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    content = serializers.DictField(required=False, default=dict)
    
    def validate_student_id(self, value):
        """Проверяем, что студент существует"""
        try:
            student = User.objects.get(id=value, role=User.Role.STUDENT)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Студент не найден")
    
    def validate(self, data):
        """Валидация дат отчета"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                "Дата начала не может быть позже даты окончания"
            )
        
        return data
