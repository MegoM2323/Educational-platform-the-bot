from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Report, ReportTemplate, ReportRecipient, AnalyticsData, ReportSchedule,
    StudentReport, TutorWeeklyReport, TeacherWeeklyReport, ParentReportPreference,
    ReportScheduleRecipient, ReportScheduleExecution
)
from accounts.models import StudentProfile

User = get_user_model()


class ReportListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка отчетов
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    target_students_count = serializers.SerializerMethodField()
    target_parents_count = serializers.SerializerMethodField()
    recipients_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = (
            'id', 'title', 'description', 'type', 'status', 'author', 'author_name',
            'target_students_count', 'target_parents_count', 'recipients_count',
            'start_date', 'end_date', 'is_auto_generated', 'generation_frequency',
            'created_at', 'generated_at', 'sent_at'
        )
    
    def get_target_students_count(self, obj):
        return obj.target_students.count()
    
    def get_target_parents_count(self, obj):
        return obj.target_parents.count()
    
    def get_recipients_count(self, obj):
        return obj.recipients.count()


class ReportDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального просмотра отчета
    """
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    target_students = serializers.SerializerMethodField()
    target_parents = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    
    class Meta:
        model = Report
        fields = (
            'id', 'title', 'description', 'type', 'status', 'author', 'author_name',
            'target_students', 'target_parents', 'start_date', 'end_date',
            'content', 'file', 'is_auto_generated', 'generation_frequency',
            'created_at', 'updated_at', 'generated_at', 'sent_at', 'recipients'
        )
    
    def get_target_students(self, obj):
        return [{
            'id': student.id,
            'name': student.get_full_name(),
            'role': student.role
        } for student in obj.target_students.all()]
    
    def get_target_parents(self, obj):
        return [{
            'id': parent.id,
            'name': parent.get_full_name(),
            'role': parent.role
        } for parent in obj.target_parents.all()]
    
    def get_recipients(self, obj):
        return ReportRecipientSerializer(obj.recipients.all(), many=True).data


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания отчета
    """
    class Meta:
        model = Report
        fields = (
            'title', 'description', 'type', 'target_students', 'target_parents',
            'start_date', 'end_date', 'content', 'is_auto_generated', 'generation_frequency'
        )
    
    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class ReportTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for report templates with validation for sections and layout.
    Supports template inheritance and versioning.
    """
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    parent_template_name = serializers.CharField(
        source='parent_template.name',
        read_only=True,
        required=False
    )
    child_templates_count = serializers.SerializerMethodField()
    has_child_templates = serializers.SerializerMethodField()

    class Meta:
        model = ReportTemplate
        fields = (
            'id', 'name', 'description', 'type', 'sections', 'layout_config',
            'default_format', 'template_content', 'is_default', 'is_archived',
            'created_by', 'created_by_name', 'parent_template', 'parent_template_name',
            'version', 'previous_version', 'child_templates_count', 'has_child_templates',
            'archived_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'archived_at', 'version')

    def get_child_templates_count(self, obj):
        """Count child templates inherited from this one."""
        return obj.child_templates.filter(is_archived=False).count()

    def get_has_child_templates(self, obj):
        """Check if template has child templates."""
        return obj.child_templates.filter(is_archived=False).exists()

    def validate_sections(self, value):
        """Validate section configuration."""
        if not value:  # Empty sections is allowed
            return value

        if not isinstance(value, list):
            raise serializers.ValidationError("Sections must be a list")

        valid_section_types = [
            'summary', 'metrics', 'progress', 'achievements', 'concerns',
            'recommendations', 'attendance', 'grades', 'performance',
            'engagement', 'behavioral', 'custom'
        ]

        for idx, section in enumerate(value):
            if not isinstance(section, dict):
                raise serializers.ValidationError(f"Section {idx} must be a dictionary")

            if 'name' not in section:
                raise serializers.ValidationError(f"Section {idx} must have 'name' field")

            if section['name'] not in valid_section_types:
                raise serializers.ValidationError(
                    f"Section name '{section['name']}' is invalid. "
                    f"Valid types: {', '.join(valid_section_types)}"
                )

            if 'fields' in section:
                if not isinstance(section['fields'], list):
                    raise serializers.ValidationError(f"Section {idx} 'fields' must be a list")

                if not section['fields']:
                    raise serializers.ValidationError(
                        f"Section {idx} must have at least one field"
                    )

        return value

    def validate_layout_config(self, value):
        """Validate layout configuration."""
        if not value:  # Empty config is allowed
            return value

        if not isinstance(value, dict):
            raise serializers.ValidationError("Layout config must be a dictionary")

        valid_orientations = ['portrait', 'landscape']
        valid_page_sizes = ['a4', 'letter', 'legal', 'a3', 'a5']

        if 'orientation' in value:
            if value['orientation'] not in valid_orientations:
                raise serializers.ValidationError(
                    f"Invalid orientation. Valid: {', '.join(valid_orientations)}"
                )

        if 'page_size' in value:
            if value['page_size'] not in valid_page_sizes:
                raise serializers.ValidationError(
                    f"Invalid page size. Valid: {', '.join(valid_page_sizes)}"
                )

        if 'margins' in value:
            margins = value['margins']
            if not isinstance(margins, dict):
                raise serializers.ValidationError("Margins must be a dictionary")

            for margin_key in ['top', 'bottom', 'left', 'right']:
                if margin_key in margins:
                    try:
                        float(margins[margin_key])
                    except (TypeError, ValueError):
                        raise serializers.ValidationError(
                            f"Margin '{margin_key}' must be numeric"
                        )

        return value

    def create(self, validated_data):
        """Create template with current user as creator."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ReportRecipientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получателей отчетов
    """
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    recipient_role = serializers.CharField(source='recipient.role', read_only=True)
    
    class Meta:
        model = ReportRecipient
        fields = (
            'id', 'report', 'recipient', 'recipient_name', 'recipient_role',
            'is_sent', 'sent_at', 'read_at'
        )
        read_only_fields = ('id', 'sent_at', 'read_at')


class AnalyticsDataSerializer(serializers.ModelSerializer):
    """
    Сериализатор для аналитических данных
    """
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    
    class Meta:
        model = AnalyticsData
        fields = (
            'id', 'student', 'student_name', 'metric_type', 'value', 'unit',
            'date', 'period_start', 'period_end', 'metadata', 'created_at'
        )
        read_only_fields = ('id', 'created_at')


class ReportScheduleSerializer(serializers.ModelSerializer):
    """
    Сериализатор для расписания отчетов
    """
    report_template_name = serializers.CharField(source='report_template.name', read_only=True)
    
    class Meta:
        model = ReportSchedule
        fields = (
            'id', 'report_template', 'report_template_name', 'frequency',
            'day_of_week', 'day_of_month', 'time', 'is_active',
            'last_generated', 'next_generation', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'last_generated', 'next_generation', 'created_at', 'updated_at')


class ReportStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики отчетов
    """
    total_reports = serializers.IntegerField()
    draft_reports = serializers.IntegerField()
    generated_reports = serializers.IntegerField()
    sent_reports = serializers.IntegerField()
    auto_generated_reports = serializers.IntegerField()
    templates_count = serializers.IntegerField()
    active_schedules = serializers.IntegerField()


class StudentProgressSerializer(serializers.Serializer):
    """
    Сериализатор для прогресса студента
    """
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    progress_percentage = serializers.FloatField()
    completed_assignments = serializers.IntegerField()
    total_assignments = serializers.IntegerField()
    average_score = serializers.FloatField()
    materials_studied = serializers.IntegerField()
    streak_days = serializers.IntegerField()
    last_activity = serializers.DateTimeField()


class ClassPerformanceSerializer(serializers.Serializer):
    """
    Сериализатор для успеваемости класса
    """
    class_name = serializers.CharField()
    total_students = serializers.IntegerField()
    average_progress = serializers.FloatField()
    average_score = serializers.FloatField()
    completion_rate = serializers.FloatField()
    top_performers = StudentProgressSerializer(many=True)
    struggling_students = StudentProgressSerializer(many=True)


class StudentReportSerializer(serializers.ModelSerializer):
    """Сериализатор персонального отчёта студента."""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentReport
        fields = (
            'id', 'title', 'description', 'report_type', 'status',
            'teacher', 'teacher_name', 'student', 'student_name', 'parent', 'parent_name',
            'period_start', 'period_end', 'content', 'overall_grade',
            'progress_percentage', 'attendance_percentage', 'behavior_rating',
            'recommendations', 'concerns', 'achievements', 'attachment',
            'show_to_parent', 'parent_acknowledged', 'parent_acknowledged_at',
            'created_at', 'updated_at', 'sent_at', 'read_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'sent_at', 'read_at', 'status', 'parent_acknowledged_at')

    def get_parent_name(self, obj):
        return obj.parent.get_full_name() if obj.parent else None


class StudentReportCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания персонального отчёта студента."""
    class Meta:
        model = StudentReport
        fields = (
            'student', 'title', 'description', 'report_type', 'period_start', 'period_end',
            'content', 'overall_grade', 'progress_percentage', 'attendance_percentage',
            'behavior_rating', 'recommendations', 'concerns', 'achievements', 'attachment',
            'show_to_parent'
        )

    def create(self, validated_data):
        request = self.context['request']
        teacher = request.user
        return StudentReport.objects.create(teacher=teacher, **validated_data)


class ParentReportPreferenceSerializer(serializers.ModelSerializer):
    """Сериализатор для настроек видимости отчетов родителя."""
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)

    class Meta:
        model = ParentReportPreference
        fields = (
            'id', 'parent', 'parent_name', 'notify_on_report_created',
            'notify_on_grade_posted', 'show_grades', 'show_progress',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'parent', 'created_at', 'updated_at')


class TutorWeeklyReportSerializer(serializers.ModelSerializer):
    """Сериализатор еженедельного отчета тьютора"""
    tutor_name = serializers.CharField(source='tutor.get_full_name', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    parent_name = serializers.SerializerMethodField()
    attendance_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TutorWeeklyReport
        fields = (
            'id', 'tutor', 'tutor_name', 'student', 'student_name', 'parent', 'parent_name',
            'week_start', 'week_end', 'title', 'summary', 'academic_progress',
            'behavior_notes', 'achievements', 'concerns', 'recommendations',
            'attendance_days', 'total_days', 'attendance_percentage', 'progress_percentage',
            'status', 'attachment', 'created_at', 'updated_at', 'sent_at', 'read_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'sent_at', 'read_at', 'status')
    
    def get_parent_name(self, obj):
        """Возвращает имя родителя или пустую строку, если родитель не назначен"""
        return obj.parent.get_full_name() if obj.parent else 'Не назначен'
    
    def get_attendance_percentage(self, obj):
        if obj.total_days > 0:
            return round((obj.attendance_days / obj.total_days) * 100, 2)
        return 0


class TutorWeeklyReportCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания еженедельного отчета тьютора"""
    class Meta:
        model = TutorWeeklyReport
        fields = (
            'student', 'week_start', 'week_end', 'title', 'summary', 'academic_progress',
            'behavior_notes', 'achievements', 'concerns', 'recommendations',
            'attendance_days', 'total_days', 'progress_percentage', 'attachment'
        )
    
    def validate_student(self, value):
        """Проверяем, что студент закреплен за текущим тьютором"""
        request = self.context['request']
        tutor = request.user
        
        # Проверяем, что это действительно студент
        if value.role != 'student':
            raise serializers.ValidationError("Выбранный пользователь не является студентом")
        
        # Проверяем, что студент закреплен за этим тьютором
        try:
            student_profile = StudentProfile.objects.select_related('tutor').get(user=value)
            if not student_profile.tutor_id:
                raise serializers.ValidationError("У студента не назначен тьютор")
            if student_profile.tutor_id != tutor.id:
                raise serializers.ValidationError("Студент не закреплен за вами")
        except StudentProfile.DoesNotExist:
            raise serializers.ValidationError("Профиль студента не найден")
        
        return value
    
    def create(self, validated_data):
        request = self.context['request']
        tutor = request.user
        student = validated_data['student']
        week_start = validated_data.get('week_start')
        
        # Получаем родителя из профиля студента
        parent = None
        try:
            student_profile = StudentProfile.objects.select_related('parent').get(user=student)
            if student_profile.parent_id:
                parent = student_profile.parent
        except StudentProfile.DoesNotExist:
            # Профиль должен существовать, так как мы проверили в validate_student
            pass
        
        # Проверяем, существует ли уже отчет для этой недели
        # unique_together = ['tutor', 'student', 'week_start']
        try:
            existing_report = TutorWeeklyReport.objects.get(
                tutor=tutor,
                student=student,
                week_start=week_start
            )
            # Если отчет существует, обновляем его
            for key, value in validated_data.items():
                if key != 'student':
                    setattr(existing_report, key, value)
            if parent:
                existing_report.parent = parent
            existing_report.save()
            return existing_report
        except TutorWeeklyReport.DoesNotExist:
            # Отчета нет, создаем новый
            pass
        except Exception as e:
            # Если произошла другая ошибка, пробрасываем её
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                raise serializers.ValidationError({
                    'week_start': f'Отчет за период с {week_start} уже существует. Выберите другой период или отредактируйте существующий отчет.'
                })
            raise
        
        # Создаем отчет
        try:
            report = TutorWeeklyReport.objects.create(
                tutor=tutor,
                student=student,
                parent=parent,
                **{k: v for k, v in validated_data.items() if k != 'student'}
            )
            return report
        except Exception as e:
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                raise serializers.ValidationError({
                    'week_start': f'Отчет за период с {week_start} уже существует. Выберите другой период или отредактируйте существующий отчет.'
                })
            raise


class TeacherWeeklyReportSerializer(serializers.ModelSerializer):
    """Сериализатор еженедельного отчета преподавателя"""
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    tutor_name = serializers.SerializerMethodField()
    subject_name = serializers.SerializerMethodField()
    subject_color = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherWeeklyReport
        fields = (
            'id', 'teacher', 'teacher_name', 'student', 'student_name', 'tutor', 'tutor_name',
            'subject', 'subject_name', 'subject_color', 'week_start', 'week_end',
            'title', 'summary', 'academic_progress', 'performance_notes',
            'achievements', 'concerns', 'recommendations',
            'assignments_completed', 'assignments_total', 'completion_percentage',
            'average_score', 'attendance_percentage', 'status', 'attachment',
            'created_at', 'updated_at', 'sent_at', 'read_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'sent_at', 'read_at', 'status')
    
    def get_tutor_name(self, obj):
        """Возвращает имя тьютора или пустую строку, если тьютор не назначен"""
        return obj.tutor.get_full_name() if obj.tutor else 'Не назначен'
    
    def get_subject_color(self, obj):
        """Возвращает цвет предмета"""
        return obj.subject.color if obj.subject else '#808080'
    
    def get_subject_name(self, obj):
        """Возвращает кастомное название предмета из enrollment или стандартное название"""
        try:
            if not obj.subject_id:
                return 'Предмет не указан'
            from materials.models import SubjectEnrollment
            enrollment = SubjectEnrollment.objects.filter(
                student_id=obj.student_id,
                teacher_id=obj.teacher_id,
                subject_id=obj.subject_id,
                is_active=True
            ).select_related('subject').first()
            if enrollment:
                return enrollment.get_subject_name()
        except Exception as e:
            # Логируем ошибку, но не падаем
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error getting subject name for report {obj.id}: {e}")
        # Fallback на стандартное название, если enrollment не найден
        if obj.subject:
            return obj.subject.name
        return 'Предмет не указан'
    
    def get_completion_percentage(self, obj):
        if obj.assignments_total > 0:
            return round((obj.assignments_completed / obj.assignments_total) * 100, 2)
        return 0


class TeacherWeeklyReportCreateSerializer(serializers.ModelSerializer):
    """Сериализатор создания еженедельного отчета преподавателя"""
    class Meta:
        model = TeacherWeeklyReport
        fields = (
            'student', 'subject', 'week_start', 'week_end', 'title', 'summary',
            'academic_progress', 'performance_notes', 'achievements', 'concerns',
            'recommendations', 'assignments_completed', 'assignments_total',
            'average_score', 'attendance_percentage', 'attachment'
        )
    
    def validate_student(self, value):
        """Проверяем, что это студент"""
        if value.role != 'student':
            raise serializers.ValidationError("Выбранный пользователь не является студентом")
        return value
    
    def validate(self, data):
        """Проверяем, что студент зачислен на указанный предмет у текущего преподавателя"""
        request = self.context['request']
        teacher = request.user
        student = data.get('student')
        subject = data.get('subject')
        
        if not student or not subject:
            raise serializers.ValidationError({
                'student': 'Необходимо указать студента',
                'subject': 'Необходимо указать предмет'
            })
        
        from materials.models import SubjectEnrollment
        if not SubjectEnrollment.objects.filter(
            student=student,
            teacher=teacher,
            subject=subject,
            is_active=True
        ).exists():
            raise serializers.ValidationError({
                'subject': 'Студент не зачислен на этот предмет у вас'
            })
        
        return data
    
    def create(self, validated_data):
        request = self.context['request']
        teacher = request.user
        student = validated_data['student']
        subject = validated_data.get('subject')
        week_start = validated_data.get('week_start')
        
        # Получаем тьютора из профиля студента
        tutor = None
        try:
            student_profile = StudentProfile.objects.select_related('tutor').get(user=student)
            if student_profile.tutor_id:
                tutor = student_profile.tutor
        except StudentProfile.DoesNotExist:
            # Профиль должен существовать для студента
            pass
        
        # Проверяем, существует ли уже отчет для этой недели и предмета
        # unique_together = ['teacher', 'student', 'subject', 'week_start']
        try:
            existing_report = TeacherWeeklyReport.objects.get(
                teacher=teacher,
                student=student,
                subject=subject,
                week_start=week_start
            )
            # Если отчет существует, обновляем его
            for key, value in validated_data.items():
                if key not in ['student', 'subject']:
                    setattr(existing_report, key, value)
            if tutor:
                existing_report.tutor = tutor
            existing_report.save()
            return existing_report
        except TeacherWeeklyReport.DoesNotExist:
            # Отчета нет, создаем новый
            pass
        except Exception as e:
            # Если произошла другая ошибка, пробрасываем её
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                raise serializers.ValidationError({
                    'week_start': f'Отчет за период с {week_start} по предмету уже существует. Выберите другой период или отредактируйте существующий отчет.'
                })
            raise
        
        # Создаем отчет
        try:
            report = TeacherWeeklyReport.objects.create(
                teacher=teacher,
                student=student,
                subject=subject,
                tutor=tutor,
                **{k: v for k, v in validated_data.items() if k not in ['student', 'subject']}
            )
            return report
        except Exception as e:
            from django.db import IntegrityError
            if isinstance(e, IntegrityError):
                raise serializers.ValidationError({
                    'week_start': f'Отчет за период с {week_start} по предмету уже существует. Выберите другой период или отредактируйте существующий отчет.'
                })
            raise



class ReportScheduleRecipientSerializer(serializers.ModelSerializer):
    """Serializer for report schedule recipients."""
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)

    class Meta:
        model = ReportScheduleRecipient
        fields = (
            'id', 'schedule', 'recipient', 'recipient_email', 'recipient_name',
            'is_subscribed', 'unsubscribe_token', 'added_at', 'unsubscribed_at'
        )
        read_only_fields = ('id', 'unsubscribe_token', 'added_at', 'unsubscribed_at')


class ReportScheduleExecutionSerializer(serializers.ModelSerializer):
    """Serializer for report schedule execution tracking."""
    schedule_name = serializers.CharField(source='schedule.name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    success_rate_percent = serializers.SerializerMethodField()

    class Meta:
        model = ReportScheduleExecution
        fields = (
            'id', 'schedule', 'schedule_name', 'status',
            'total_recipients', 'successful_sends', 'failed_sends',
            'error_message', 'started_at', 'completed_at',
            'duration_seconds', 'success_rate_percent'
        )
        read_only_fields = ('id', 'started_at', 'completed_at')

    def get_duration_seconds(self, obj):
        return obj.duration

    def get_success_rate_percent(self, obj):
        return obj.success_rate


class ReportScheduleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for report schedules with recipients."""
    report_template_name = serializers.CharField(source='report_template.name', read_only=True)
    recipients = ReportScheduleRecipientSerializer(source='recipient_entries', many=True, read_only=True)
    active_recipients_count = serializers.SerializerMethodField()
    recent_executions = serializers.SerializerMethodField()

    class Meta:
        model = ReportSchedule
        fields = (
            'id', 'name', 'report_template', 'report_template_name',
            'report_type', 'frequency', 'day_of_week', 'day_of_month',
            'time', 'export_format', 'created_by', 'is_active',
            'last_sent', 'last_generated', 'next_scheduled',
            'created_at', 'updated_at', 'recipients', 'active_recipients_count',
            'recent_executions'
        )
        read_only_fields = (
            'id', 'last_sent', 'last_generated', 'next_scheduled',
            'created_at', 'updated_at'
        )

    def get_active_recipients_count(self, obj):
        return obj.recipient_entries.filter(is_subscribed=True).count()

    def get_recent_executions(self, obj):
        recent = obj.executions.all()[:5]
        return ReportScheduleExecutionSerializer(recent, many=True).data


class ReportScheduleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating report schedules."""

    class Meta:
        model = ReportSchedule
        fields = (
            'name', 'report_type', 'frequency', 'day_of_week', 'day_of_month',
            'time', 'export_format', 'is_active'
        )

    def validate(self, data):
        """Validate schedule configuration."""
        frequency = data.get('frequency')
        day_of_week = data.get('day_of_week')
        day_of_month = data.get('day_of_month')

        if frequency == 'weekly' and not day_of_week:
            raise serializers.ValidationError({
                'day_of_week': 'Day of week is required for weekly schedules'
            })

        if frequency == 'monthly' and not day_of_month:
            raise serializers.ValidationError({
                'day_of_month': 'Day of month is required for monthly schedules'
            })

        return data

    def create(self, validated_data):
        """Create schedule with current user as creator."""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        return super().create(validated_data)
