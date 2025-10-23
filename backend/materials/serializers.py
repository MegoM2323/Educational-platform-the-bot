from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Subject, Material, MaterialProgress, MaterialComment

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
