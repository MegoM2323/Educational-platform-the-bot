from rest_framework import serializers
from django.contrib.auth import get_user_model

from materials.models import Subject, SubjectEnrollment
from .models import StudentProfile


User = get_user_model()


class TutorStudentCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    grade = serializers.CharField(max_length=10)
    goal = serializers.CharField(allow_blank=True, required=False)
    parent_first_name = serializers.CharField(max_length=150)
    parent_last_name = serializers.CharField(max_length=150)
    parent_email = serializers.EmailField(required=False, allow_blank=True)
    parent_phone = serializers.CharField(required=False, allow_blank=True)


class TutorStudentSerializer(serializers.ModelSerializer):
    tutor_name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    full_name = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user_id', 'full_name', 'grade', 'goal', 'tutor', 'tutor_name',
            'parent', 'parent_name', 'progress_percentage', 'subjects'
        )

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else ''

    def get_tutor_name(self, obj):
        if obj.tutor:
            return obj.tutor.get_full_name() or obj.tutor.username
        return None

    def get_parent_name(self, obj):
        if obj.parent:
            return obj.parent.get_full_name() or obj.parent.username
        return None
    
    def get_subjects(self, obj):
        """Возвращает список назначенных предметов студента с кастомными названиями"""
        from materials.models import SubjectEnrollment
        enrollments = SubjectEnrollment.objects.filter(
            student=obj.user,
            is_active=True
        ).select_related('subject', 'teacher')
        
        return [
            {
                'id': enrollment.subject.id,
                'name': enrollment.get_subject_name(),
                'teacher_name': enrollment.teacher.get_full_name(),
                'enrollment_id': enrollment.id,
            }
            for enrollment in enrollments
        ]


class SubjectAssignSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    subject_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    teacher_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        subject_id = attrs.get('subject_id')
        subject_name = attrs.get('subject_name', '').strip() if attrs.get('subject_name') else ''
        teacher_id = attrs.get('teacher_id')

        # Валидация: должен быть указан либо subject_id, либо subject_name, но не оба
        if subject_id and subject_name:
            raise serializers.ValidationError({
                'subject_id': 'Укажите либо subject_id, либо subject_name, но не оба одновременно',
                'subject_name': 'Укажите либо subject_id, либо subject_name, но не оба одновременно'
            })
        
        if not subject_id and not subject_name:
            raise serializers.ValidationError({
                'subject_id': 'Необходимо указать либо subject_id, либо subject_name'
            })

        # Если указан subject_id, используем существующий предмет
        if subject_id:
            try:
                attrs['subject'] = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                raise serializers.ValidationError({'subject_id': 'Предмет не найден'})
        # Если указано subject_name, создаем или получаем предмет
        elif subject_name:
            if len(subject_name) < 2:
                raise serializers.ValidationError({'subject_name': 'Название предмета должно содержать минимум 2 символа'})
            if len(subject_name) > 200:
                raise serializers.ValidationError({'subject_name': 'Название предмета не должно превышать 200 символов'})
            from .tutor_service import SubjectAssignmentService
            attrs['subject'] = SubjectAssignmentService.get_or_create_subject(subject_name)

        # Валидация преподавателя - обязателен
        if teacher_id is None:
            raise serializers.ValidationError({'teacher_id': 'Необходимо указать преподавателя'})
        
        try:
            teacher = User.objects.get(id=teacher_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'teacher_id': 'Пользователь не найден'})

        if teacher.role != User.Role.TEACHER:
            raise serializers.ValidationError({'teacher_id': 'Пользователь не является преподавателем'})
        
        if not teacher.is_active:
            raise serializers.ValidationError({'teacher_id': 'Указанный преподаватель неактивен'})

        attrs['teacher'] = teacher

        return attrs


class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.SerializerMethodField()
    custom_subject_name = serializers.CharField(read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = SubjectEnrollment
        fields = (
            'id', 'student', 'subject', 'subject_name', 'custom_subject_name', 'teacher', 'teacher_name',
            'enrolled_at', 'is_active'
        )

    def get_subject_name(self, obj):
        """Возвращает кастомное название или стандартное название предмета"""
        return obj.get_subject_name()

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return None



class SubjectBulkAssignItemSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    subject_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    teacher_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        subject_id = attrs.get('subject_id')
        subject_name = attrs.get('subject_name', '').strip() if attrs.get('subject_name') else ''
        teacher_id = attrs.get('teacher_id')

        # Валидация: должен быть указан либо subject_id, либо subject_name, но не оба
        if subject_id and subject_name:
            raise serializers.ValidationError({
                'subject_id': 'Укажите либо subject_id, либо subject_name, но не оба одновременно',
                'subject_name': 'Укажите либо subject_id, либо subject_name, но не оба одновременно'
            })
        
        if not subject_id and not subject_name:
            raise serializers.ValidationError({
                'subject_id': 'Необходимо указать либо subject_id, либо subject_name'
            })

        # Если указан subject_id, используем существующий предмет
        if subject_id:
            try:
                attrs['subject'] = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                raise serializers.ValidationError({'subject_id': 'Предмет не найден'})
        # Если указано subject_name, создаем или получаем предмет
        elif subject_name:
            if len(subject_name) < 2:
                raise serializers.ValidationError({'subject_name': 'Название предмета должно содержать минимум 2 символа'})
            if len(subject_name) > 200:
                raise serializers.ValidationError({'subject_name': 'Название предмета не должно превышать 200 символов'})
            from .tutor_service import SubjectAssignmentService
            attrs['subject'] = SubjectAssignmentService.get_or_create_subject(subject_name)

        # Валидация преподавателя - обязателен
        if teacher_id is None:
            raise serializers.ValidationError({'teacher_id': 'Необходимо указать преподавателя'})
        
        try:
            teacher = User.objects.get(id=teacher_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'teacher_id': 'Пользователь не найден'})

        if teacher.role != User.Role.TEACHER:
            raise serializers.ValidationError({'teacher_id': 'Пользователь не является преподавателем'})
        
        if not teacher.is_active:
            raise serializers.ValidationError({'teacher_id': 'Указанный преподаватель неактивен'})

        attrs['teacher'] = teacher

        return attrs


class SubjectBulkAssignSerializer(serializers.Serializer):
    items = SubjectBulkAssignItemSerializer(many=True)

