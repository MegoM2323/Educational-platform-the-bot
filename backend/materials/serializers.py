from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.file_utils import build_secure_file_url
from .models import Subject, Material, MaterialProgress, MaterialComment, MaterialSubmission, MaterialFeedback, SubjectEnrollment, SubjectPayment, StudyPlan, StudyPlanFile, BulkAssignmentAuditLog
from .validators import (
    validate_file_type,
    validate_file_size,
    validate_title_length,
    validate_description_length,
    MaterialFileValidator
)

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
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = (
            'id', 'title', 'description', 'content', 'author', 'author_name',
            'subject', 'subject_name', 'type', 'status', 'file', 'file_url', 'video_url',
            'is_public', 'assigned_to', 'assigned_to_names', 'tags',
            'difficulty_level', 'created_at', 'updated_at', 'published_at',
            'progress', 'comments_count'
        )
    
    def get_file_url(self, obj):
        """Возвращает абсолютный URL файла с правильной схемой (HTTP/HTTPS)"""
        request = self.context.get('request')
        return build_secure_file_url(obj.file, request)
    
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
    Сериализатор для создания материала с расширенной валидацией
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
        Валидация загружаемого файла:
        - Размер максимум 50MB
        - Поддерживаемые типы: pdf, doc, docx, xls, xlsx, ppt, pptx, mp4, mp3
        """
        if value:
            # Проверка размера файла (50MB максимум)
            validate_file_size(value)

            # Проверка типа файла
            validate_file_type(value)

        return value

    def validate_title(self, value):
        """
        Валидация заголовка материала (макс 200 символов)
        """
        validate_title_length(value)
        return value.strip() if value else value

    def validate_description(self, value):
        """
        Валидация описания материала (макс 5000 символов)
        """
        if value:
            validate_description_length(value)
        return value

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
    Serializer for material study progress.

    Handles edge cases:
    - Negative progress_percentage (clamped to 0)
    - Progress > 100 (capped at 100)
    - Negative time_spent (clamped to 0)
    - NULL values (converted to defaults)
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

    def validate_progress_percentage(self, value):
        """
        Validate progress_percentage edge cases:
        - NULL defaults to 0
        - Negative values clamped to 0
        - Values > 100 capped to 100
        """
        if value is None:
            return 0

        try:
            value = int(value)
        except (ValueError, TypeError):
            raise serializers.ValidationError(
                "progress_percentage должен быть числом"
            )

        if value < 0:
            return 0
        if value > 100:
            return 100

        return value

    def validate_time_spent(self, value):
        """
        Validate time_spent edge cases:
        - NULL defaults to 0
        - Negative values clamped to 0
        """
        if value is None:
            return 0

        try:
            value = int(value)
        except (ValueError, TypeError):
            raise serializers.ValidationError(
                "time_spent должен быть числом (минуты)"
            )

        if value < 0:
            return 0

        return value

    def update(self, instance, validated_data):
        """
        Update progress record.

        Features:
        - Prevent progress rollback (progress only increases)
        - Auto-complete at 100%
        - Set completed_at on first completion
        """
        # Prevent progress rollback
        if 'progress_percentage' in validated_data:
            new_progress = validated_data['progress_percentage']
            if new_progress < instance.progress_percentage:
                # Keep existing progress (prevent rollback)
                validated_data['progress_percentage'] = instance.progress_percentage

        # Auto-complete at 100%
        if validated_data.get('progress_percentage', instance.progress_percentage) >= 100:
            validated_data['is_completed'] = True

        # Set completed_at on first completion
        if validated_data.get('is_completed') and not instance.is_completed:
            from django.utils import timezone
            validated_data['completed_at'] = timezone.now()

        return super().update(instance, validated_data)


class MaterialCommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для комментариев к материалам (верхнего уровня)

    Поля:
    - id: ID комментария
    - material: ID материала
    - author: ID автора
    - author_name: Полное имя автора (read-only)
    - content: Текст комментария
    - is_question: Является ли вопросом
    - parent_comment: ID родительского комментария (для потокования)
    - is_deleted: Удален ли (soft delete)
    - is_approved: Одобрен ли (для модерации)
    - reply_count: Количество ответов (read-only, аннотация из viewset)
    - created_at: Дата создания
    - updated_at: Дата обновления
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    reply_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = MaterialComment
        fields = (
            'id', 'material', 'author', 'author_name', 'content',
            'is_question', 'parent_comment', 'is_deleted', 'is_approved',
            'reply_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'author', 'created_at', 'updated_at', 'reply_count')

    def create(self, validated_data):
        """Создать комментарий с текущим пользователем как автором"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class MaterialCommentReplySerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответов на комментарии (потокование)

    Похож на MaterialCommentSerializer но используется для отображения
    ответов в списке replies с дополнительной информацией о возможности
    удаления текущим пользователем.

    Поля:
    - id: ID ответа
    - author_id: ID автора
    - author_name: Полное имя автора
    - content: Текст ответа
    - is_question: Является ли вопросом
    - created_at: Дата создания
    - can_delete: Может ли текущий пользователь удалить этот ответ
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = MaterialComment
        fields = (
            'id', 'author_id', 'author_name', 'content',
            'is_question', 'created_at', 'can_delete'
        )
        read_only_fields = ('id', 'author_name', 'author_id', 'created_at', 'can_delete')

    def get_can_delete(self, obj) -> bool:
        """Проверить может ли текущий пользователь удалить этот комментарий"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        # Автор может удалить свой комментарий, учителя/админы могут удалить любой
        return obj.author_id == request.user.id or request.user.role in ['teacher', 'admin']


# Сериализаторы для родительского дашборда

class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для зачислений на предметы
    """
    subject_name = serializers.SerializerMethodField()
    subject_color = serializers.CharField(source='subject.color', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    custom_subject_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = SubjectEnrollment
        fields = (
            'id', 'student', 'subject', 'subject_name', 'subject_color', 'custom_subject_name',
            'teacher', 'teacher_name', 'enrolled_at', 'is_active'
        )
        read_only_fields = ('id', 'enrolled_at')
    
    def get_subject_name(self, obj):
        """Возвращает кастомное название или стандартное название предмета"""
        return obj.get_subject_name()


class SubjectEnrollmentCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания зачисления на предмет (T_MAT_006)

    Используется для POST /api/subjects/{id}/enroll/ endpoint
    Выполняет валидацию перед созданием зачисления
    """
    student_id = serializers.IntegerField(required=True)
    teacher_id = serializers.IntegerField(required=True)
    custom_subject_name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        help_text="Кастомное название предмета (опционально)"
    )

    def validate_student_id(self, value):
        """Валидация student_id"""
        from .enrollment_service import SubjectEnrollmentService
        try:
            SubjectEnrollmentService.validate_student_exists(value)
        except serializers.ValidationError:
            raise
        return value

    def validate_teacher_id(self, value):
        """Валидация teacher_id"""
        from .enrollment_service import SubjectEnrollmentService
        try:
            SubjectEnrollmentService.validate_teacher_exists(value)
        except serializers.ValidationError:
            raise
        return value

    def validate(self, data):
        """
        Комбинированная валидация
        """
        from .enrollment_service import SubjectEnrollmentService

        subject_id = self.context.get('subject_id')

        # Валидация дублирования зачисления
        student = User.objects.get(id=data['student_id'])
        subject = Subject.objects.get(id=subject_id)
        teacher = User.objects.get(id=data['teacher_id'])

        existing = SubjectEnrollmentService.check_duplicate_enrollment(
            student, subject, teacher
        )
        if existing:
            raise serializers.ValidationError(
                f"Студент уже зачислен на этот предмет к этому преподавателю"
            )

        # Проверка на самозачисление
        SubjectEnrollmentService.prevent_self_enrollment_as_teacher(student, teacher)

        return data


class SubjectEnrollmentCancelSerializer(serializers.Serializer):
    """
    Сериализатор для отмены зачисления (T_MAT_006)

    Используется для DELETE /api/subjects/{id}/unenroll/ endpoint
    """
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Причина отмены (опционально)"
    )


class MyEnrollmentsSerializer(serializers.Serializer):
    """
    Сериализатор для получения зачислений текущего пользователя (T_MAT_006)

    Используется для GET /api/subjects/my-enrollments/ endpoint
    """
    id = serializers.IntegerField()
    subject = SubjectSerializer()
    teacher = serializers.SerializerMethodField()
    custom_subject_name = serializers.CharField()
    enrolled_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()

    def get_teacher(self, obj):
        """Возвращает информацию о преподавателе"""
        return {
            'id': obj.teacher.id,
            'name': obj.teacher.get_full_name(),
            'email': obj.teacher.email
        }


class SubjectPaymentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для платежей по предметам
    """
    subject_name = serializers.SerializerMethodField()
    student_name = serializers.CharField(source='enrollment.student.get_full_name', read_only=True)

    class Meta:
        model = SubjectPayment
        fields = (
            'id', 'enrollment', 'payment', 'amount', 'status',
            'due_date', 'paid_at', 'created_at', 'updated_at',
            'subject_name', 'student_name'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'paid_at')

    def get_subject_name(self, obj):
        """Возвращает кастомное название или стандартное название предмета"""
        return obj.enrollment.get_subject_name()


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
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    create_subscription = serializers.BooleanField(default=False, required=False)
    
    def validate_amount(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля")
        return value


class MaterialSubmissionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответов учеников на материалы с валидацией файлов
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
        Валидация файла ответа (максимум 50MB)
        """
        if value:
            validate_file_size(value)
            validate_file_type(value)
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


class StudyPlanFileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для файлов плана занятий
    """
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = StudyPlanFile
        fields = (
            'id', 'study_plan', 'file', 'file_url', 'name', 'file_size',
            'uploaded_by', 'uploaded_by_name', 'created_at'
        )
        read_only_fields = ('id', 'uploaded_by', 'created_at', 'file_size')
    
    def get_file_url(self, obj):
        """Возвращает URL файла с правильной схемой (HTTP/HTTPS)"""
        request = self.context.get('request')
        return build_secure_file_url(obj.file, request)


class StudyPlanSerializer(serializers.ModelSerializer):
    """
    Сериализатор для планов занятий
    """
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    subject_name = serializers.SerializerMethodField()
    subject_color = serializers.CharField(source='subject.color', read_only=True)
    files = StudyPlanFileSerializer(many=True, read_only=True, source='files.all')
    
    class Meta:
        model = StudyPlan
        fields = (
            'id', 'teacher', 'teacher_name', 'student', 'student_name',
            'subject', 'subject_name', 'subject_color', 'enrollment',
            'title', 'content', 'week_start_date', 'week_end_date',
            'status', 'created_at', 'updated_at', 'sent_at', 'files'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'sent_at', 'week_end_date')
    
    def get_subject_name(self, obj):
        """Возвращает кастомное название предмета из enrollment, если есть, иначе стандартное"""
        if obj.enrollment:
            return obj.enrollment.get_subject_name()
        return obj.subject.name
    
    def validate(self, data):
        """
        Валидация данных плана
        """
        # Проверяем, что студент зачислен на предмет к этому преподавателю
        if 'student' in data and 'subject' in data and 'teacher' in data:
            from .models import SubjectEnrollment
            try:
                enrollment = SubjectEnrollment.objects.get(
                    student=data['student'],
                    subject=data['subject'],
                    teacher=data['teacher'],
                    is_active=True
                )
                if 'enrollment' not in data:
                    data['enrollment'] = enrollment
            except SubjectEnrollment.DoesNotExist:
                raise serializers.ValidationError(
                    "Студент не зачислен на этот предмет к данному преподавателю"
                )
        
        return data
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)


class StudyPlanCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания плана занятий
    """
    class Meta:
        model = StudyPlan
        fields = (
            'student', 'subject', 'title', 'content', 'week_start_date', 'status'
        )
    
    def validate_title(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Название плана должно содержать минимум 3 символа")
        return value.strip()
    
    def validate_content(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Содержание плана должно содержать минимум 10 символов")
        return value.strip()
    
    def validate(self, data):
        """
        Валидация данных при создании
        """
        request = self.context['request']
        teacher = request.user
        
        # Проверяем, что преподаватель ведет этот предмет
        from .models import TeacherSubject
        try:
            TeacherSubject.objects.get(
                teacher=teacher,
                subject=data['subject'],
                is_active=True
            )
        except TeacherSubject.DoesNotExist:
            raise serializers.ValidationError(
                "Вы не ведете этот предмет"
            )
        
        # Проверяем, что студент зачислен на предмет к этому преподавателю
        from .models import SubjectEnrollment
        try:
            enrollment = SubjectEnrollment.objects.get(
                student=data['student'],
                subject=data['subject'],
                teacher=teacher,
                is_active=True
            )
            data['enrollment'] = enrollment
        except SubjectEnrollment.DoesNotExist:
            raise serializers.ValidationError(
                "Студент не зачислен на этот предмет к вам"
            )
        
        return data
    
    def create(self, validated_data):
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)


class StudyPlanListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка планов занятий (упрощенный)
    """
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    subject_name = serializers.SerializerMethodField()
    subject_color = serializers.CharField(source='subject.color', read_only=True)
    student = serializers.IntegerField(source='student.id', read_only=True)
    subject = serializers.IntegerField(source='subject.id', read_only=True)
    files = StudyPlanFileSerializer(many=True, read_only=True, source='files.all')

    def get_subject_name(self, obj):
        """Возвращает кастомное название предмета из enrollment, если есть, иначе стандартное"""
        if obj.enrollment:
            return obj.enrollment.get_subject_name()
        return obj.subject.name

    class Meta:
        model = StudyPlan
        fields = (
            'id', 'teacher_name', 'student_name', 'student', 'subject_name', 'subject', 'subject_color',
            'title', 'content', 'week_start_date', 'week_end_date', 'status', 'sent_at', 'created_at', 'files'
        )


class TeacherSubjectUpdateSerializer(serializers.Serializer):
    """
    Сериализатор для обновления предметов преподавателя
    """
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
        help_text="Список ID предметов для назначения преподавателю"
    )

    def validate_subject_ids(self, value):
        """
        Валидация списка ID предметов - проверяем что все предметы существуют
        """
        if not value:
            # Пустой список - удаляем все предметы
            return value

        # Проверяем что все ID существуют в базе
        from .models import Subject
        existing_subjects = Subject.objects.filter(id__in=value).values_list('id', flat=True)
        existing_ids = set(existing_subjects)
        requested_ids = set(value)

        missing_ids = requested_ids - existing_ids
        if missing_ids:
            raise serializers.ValidationError(
                f"Предметы с ID {sorted(missing_ids)} не найдены"
            )

        return value


class TeacherSubjectSerializer(serializers.Serializer):
    """
    Сериализатор для вывода связи преподаватель-предмет
    """
    id = serializers.IntegerField(source='subject.id', read_only=True)
    name = serializers.CharField(source='subject.name', read_only=True)
    description = serializers.CharField(source='subject.description', read_only=True)
    color = serializers.CharField(source='subject.color', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    assigned_at = serializers.DateTimeField(read_only=True)



class BulkAssignmentAuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for BulkAssignmentAuditLog model.
    """
    performed_by_name = serializers.CharField(source="performed_by.get_full_name", read_only=True)
    operation_display = serializers.CharField(source="get_operation_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = BulkAssignmentAuditLog
        fields = (
            "id",
            "performed_by",
            "performed_by_name",
            "operation_type",
            "operation_display",
            "status",
            "status_display",
            "total_items",
            "created_count",
            "skipped_count",
            "failed_count",
            "failed_items",
            "error_message",
            "metadata",
            "created_at",
            "completed_at",
            "duration_seconds",
        )
        read_only_fields = fields

