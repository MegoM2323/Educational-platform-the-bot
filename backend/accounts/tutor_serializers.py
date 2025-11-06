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

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user_id', 'full_name', 'grade', 'goal', 'tutor', 'tutor_name',
            'parent', 'parent_name', 'progress_percentage'
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


class SubjectAssignSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    teacher_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        subject_id = attrs['subject_id']
        teacher_id = attrs.get('teacher_id')

        try:
            attrs['subject'] = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise serializers.ValidationError({'subject_id': 'Предмет не найден'})

        if teacher_id is not None:
            try:
                teacher = User.objects.get(id=teacher_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({'teacher_id': 'Пользователь не найден'})

            if teacher.role != User.Role.TEACHER:
                raise serializers.ValidationError({'teacher_id': 'Пользователь не является преподавателем'})

            attrs['teacher'] = teacher
        else:
            attrs['teacher'] = None
        return attrs


class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = SubjectEnrollment
        fields = (
            'id', 'student', 'subject', 'subject_name', 'teacher', 'teacher_name',
            'enrolled_at', 'is_active'
        )

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.username
        return None



class SubjectBulkAssignItemSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    teacher_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        subject_id = attrs['subject_id']
        teacher_id = attrs.get('teacher_id')

        try:
            attrs['subject'] = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise serializers.ValidationError({'subject_id': 'Предмет не найден'})

        if teacher_id is not None:
            try:
                teacher = User.objects.get(id=teacher_id)
            except User.DoesNotExist:
                raise serializers.ValidationError({'teacher_id': 'Пользователь не найден'})

            if teacher.role != User.Role.TEACHER:
                raise serializers.ValidationError({'teacher_id': 'Пользователь не является преподавателем'})

            attrs['teacher'] = teacher
        else:
            attrs['teacher'] = None
        return attrs


class SubjectBulkAssignSerializer(serializers.Serializer):
    items = SubjectBulkAssignItemSerializer(many=True)

