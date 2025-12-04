import logging
from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import StudentProfile


logger = logging.getLogger(__name__)
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
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user_id', 'full_name', 'first_name', 'last_name', 'grade', 'goal', 'tutor', 'tutor_name',
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

        # Получаем ID пользователя для гарантии свежих данных
        user_id = obj.user.id if hasattr(obj.user, 'id') else obj.user.pk

        # Пробуем использовать prefetched data если доступно
        # Это избегает N+1 queries при использовании prefetch_related в view
        if hasattr(obj.user, '_prefetched_objects_cache') and 'subject_enrollments' in obj.user._prefetched_objects_cache:
            # Используем prefetched data - NO дополнительных запросов
            enrollments = [e for e in obj.user.subject_enrollments.all() if e.is_active]
            logger.debug(f"Using prefetched subject_enrollments for student {user_id}")
        else:
            # Fallback: делаем запрос если prefetch не был использован
            # Это происходит при прямых вызовах сериализатора без prefetch
            enrollments_queryset = SubjectEnrollment.objects.filter(
                student_id=user_id,
                is_active=True
            ).select_related('subject', 'teacher').order_by('-enrolled_at', '-id')
            enrollments = list(enrollments_queryset)
            logger.debug(f"Querying subject_enrollments for student {user_id} (prefetch not available)")

        result = [
            {
                'id': enrollment.subject.id,
                'name': enrollment.get_subject_name(),
                'teacher_name': enrollment.teacher.get_full_name() if enrollment.teacher else 'Не указан',
                'enrollment_id': enrollment.id,
            }
            for enrollment in enrollments
        ]

        # Логируем для отладки
        logger.debug(f"Student {user_id} ({obj.user.username}) has {len(result)} active enrollments")
        if len(result) > 0:
            for item in result:
                logger.debug(f"  - {item['name']} (teacher: {item['teacher_name']}, enrollment_id: {item['enrollment_id']})")
        else:
            logger.debug(f"No active enrollments found for student {user_id}")
            # Проверяем, есть ли вообще enrollments для этого студента (включая неактивные)
            all_enrollments_count = SubjectEnrollment.objects.filter(student_id=user_id).count()
            active_count = SubjectEnrollment.objects.filter(student_id=user_id, is_active=True).count()
            logger.debug(f"Total enrollments: {all_enrollments_count}, Active: {active_count}")

        return result


class SubjectAssignSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    subject_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    teacher_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        from materials.models import Subject
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


class SubjectEnrollmentSerializer(serializers.Serializer):
    """Serializer for SubjectEnrollment - uses manual field declaration to avoid circular imports"""
    id = serializers.IntegerField(read_only=True)
    student = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()
    custom_subject_name = serializers.CharField(read_only=True)
    teacher = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    enrolled_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField()

    def get_student(self, obj):
        """Возвращает ID студента"""
        return obj.student.id if obj.student else None

    def get_subject(self, obj):
        """Возвращает ID предмета"""
        return obj.subject.id if obj.subject else None

    def get_subject_name(self, obj):
        """Возвращает кастомное название или стандартное название предмета"""
        return obj.get_subject_name()

    def get_teacher(self, obj):
        """Возвращает ID преподавателя"""
        return obj.teacher.id if obj.teacher else None

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return None


class SubjectBulkAssignItemSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField(required=False, allow_null=True)
    subject_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    teacher_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        from materials.models import Subject
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

