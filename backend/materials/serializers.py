from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Subject, Material, MaterialProgress, MaterialComment, MaterialSubmission, MaterialFeedback, SubjectEnrollment, SubjectPayment

User = get_user_model()


class SubjectSerializer(serializers.ModelSerializer):
    """
    Сериализатор для предметов
    """
    materials_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Subject
        fields = ('id', 'name', 'description', 'color', 'materials_count')
    
    def get_materials_count(self, obj):
        return obj.materials.filter(status=Material.Status.ACTIVE).count()


class MaterialListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка материалов
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    assigned_count = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = (
            'id', 'title', 'description', 'author', 'author_name', 'subject',
            'subject_name', 'type', 'status', 'is_public', 'assigned_count',
            'difficulty_level', 'tags', 'created_at', 'published_at', 'progress'
        )
    
    def get_assigned_count(self, obj):
        return obj.assigned_to.count()
    
    def get_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = obj.progress.get(student=request.user)
                return {
                    'is_completed': progress.is_completed,
                    'progress_percentage': progress.progress_percentage,
                    'time_spent': progress.time_spent
                }
            except MaterialProgress.DoesNotExist:
                return None
        return None


class MaterialDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального просмотра материала
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    assigned_to_names = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = (
            'id', 'title', 'description', 'content', 'author', 'author_name',
            'subject', 'subject_name', 'type', 'status', 'file', 'video_url',
            'is_public', 'assigned_to', 'assigned_to_names', 'tags',
            'difficulty_level', 'created_at', 'updated_at', 'published_at',
            'progress', 'comments_count'
        )
    
    def get_assigned_to_names(self, obj):
        return [user.get_full_name() for user in obj.assigned_to.all()]
    
    def get_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = obj.progress.get(student=request.user)
                return {
                    'is_completed': progress.is_completed,
                    'progress_percentage': progress.progress_percentage,
                    'time_spent': progress.time_spent,
                    'started_at': progress.started_at,
                    'completed_at': progress.completed_at,
                    'last_accessed': progress.last_accessed
                }
            except MaterialProgress.DoesNotExist:
                return None
        return None
    
    def get_comments_count(self, obj):
        return obj.comments.count()


class MaterialCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания материала
    """
    class Meta:
        model = Material
        fields = (
            'title', 'description', 'content', 'subject', 'type', 'status',
            'file', 'video_url', 'is_public', 'assigned_to', 'tags',
            'difficulty_level'
        )
    
    def validate_file(self, value):
        """
        Валидация загружаемого файла
        """
        if value:
            # Проверка размера файла (10MB максимум)
            max_size = 10 * 1024 * 1024  # 10MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"Размер файла не должен превышать {max_size // (1024*1024)}MB"
                )
            
            # Проверка расширения файла
            allowed_extensions = ['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt', 'jpg', 'jpeg', 'png']
            file_extension = value.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Неподдерживаемый тип файла. Разрешенные форматы: {', '.join(allowed_extensions)}"
                )
        
        return value
    
    def validate_title(self, value):
        """
        Валидация заголовка материала
        """
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Заголовок должен содержать минимум 3 символа")
        return value.strip()
    
    def validate_content(self, value):
        """
        Валидация содержания материала
        """
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Содержание должно содержать минимум 10 символов")
        return value.strip()
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class MaterialProgressSerializer(serializers.ModelSerializer):
    """
    Сериализатор для прогресса изучения материала
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    material_title = serializers.CharField(source='material.title', read_only=True)
    
    class Meta:
        model = MaterialProgress
        fields = (
            'id', 'student', 'student_name', 'material', 'material_title',
            'is_completed', 'progress_percentage', 'time_spent',
            'started_at', 'completed_at', 'last_accessed'
        )
        read_only_fields = ('id', 'started_at', 'completed_at', 'last_accessed')
    
    def update(self, instance, validated_data):
        # Автоматически устанавливаем completed_at при завершении
        if validated_data.get('is_completed') and not instance.is_completed:
            from django.utils import timezone
            validated_data['completed_at'] = timezone.now()
        
        return super().update(instance, validated_data)


class MaterialCommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для комментариев к материалам
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    
    class Meta:
        model = MaterialComment
        fields = (
            'id', 'material', 'author', 'author_name', 'content',
            'is_question', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'author', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


# Сериализаторы для родительского дашборда

class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для зачислений на предметы
    """
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_color = serializers.CharField(source='subject.color', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    
    class Meta:
        model = SubjectEnrollment
        fields = (
            'id', 'student', 'subject', 'subject_name', 'subject_color',
            'teacher', 'teacher_name', 'enrolled_at', 'is_active'
        )
        read_only_fields = ('id', 'enrolled_at')


class SubjectPaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для платежей по предметам
    """
    subject_name = serializers.CharField(source='enrollment.subject.name', read_only=True)
    student_name = serializers.CharField(source='enrollment.student.get_full_name', read_only=True)
    
    class Meta:
        model = SubjectPayment
        fields = (
            'id', 'enrollment', 'payment', 'amount', 'status',
            'due_date', 'paid_at', 'created_at', 'updated_at',
            'subject_name', 'student_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'paid_at')


class ParentDashboardSerializer(serializers.Serializer):
    """
    Сериализатор для данных дашборда родителя
    """
    parent = serializers.DictField()
    children = serializers.ListField()
    total_children = serializers.IntegerField()


class ChildSubjectsSerializer(serializers.Serializer):
    """
    Сериализатор для предметов ребенка
    """
    enrollment_id = serializers.IntegerField()
    subject = serializers.DictField()
    teacher = serializers.DictField()
    enrolled_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()


class PaymentInitiationSerializer(serializers.Serializer):
    """
    Сериализатор для инициации платежа
    """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    create_subscription = serializers.BooleanField(default=False, required=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        return value


class MaterialSubmissionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответов учеников на материалы
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    material_title = serializers.CharField(source='material.title', read_only=True)
    
    class Meta:
        model = MaterialSubmission
        fields = (
            'id', 'material', 'material_title', 'student', 'student_name',
            'submission_file', 'submission_text', 'submitted_at', 'is_late'
        )
        read_only_fields = ('id', 'submitted_at', 'is_late')
    
    def validate_submission_file(self, value):
        """
        Валидация файла ответа
        """
        if value:
            max_size = 10 * 1024 * 1024  # 10MB
            if value.size > max_size:
                raise serializers.ValidationError(
                    f"Размер файла не должен превышать {max_size // (1024*1024)}MB"
                )
        return value
    
    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)


class MaterialFeedbackSerializer(serializers.ModelSerializer):
    """
    Сериализатор для фидбэка преподавателей
    """
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    student_name = serializers.CharField(source='submission.student.get_full_name', read_only=True)
    material_title = serializers.CharField(source='submission.material.title', read_only=True)
    
    class Meta:
        model = MaterialFeedback
        fields = (
            'id', 'submission', 'teacher', 'teacher_name', 'student_name',
            'material_title', 'feedback_text', 'grade', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'teacher', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)
