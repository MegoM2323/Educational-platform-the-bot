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
    tutor_name = serializers.CharField(source='tutor.get_full_name', read_only=True)
    parent_name = serializers.CharField(source='parent.get_full_name', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            'id', 'user_id', 'full_name', 'grade', 'goal', 'tutor', 'tutor_name',
            'parent', 'parent_name', 'progress_percentage'
        )

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class SubjectAssignSerializer(serializers.Serializer):
    subject_id = serializers.IntegerField()
    teacher_id = serializers.IntegerField()

    def validate(self, attrs):
        subject_id = attrs['subject_id']
        teacher_id = attrs['teacher_id']

        try:
            attrs['subject'] = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            raise serializers.ValidationError({'subject_id': 'Предмет не найден'})

        try:
            teacher = User.objects.get(id=teacher_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'teacher_id': 'Пользователь не найден'})

        if teacher.role != User.Role.TEACHER:
            raise serializers.ValidationError({'teacher_id': 'Пользователь не является преподавателем'})

        attrs['teacher'] = teacher
        return attrs


class SubjectEnrollmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)

    class Meta:
        model = SubjectEnrollment
        fields = (
            'id', 'student', 'subject', 'subject_name', 'teacher', 'teacher_name',
            'enrolled_at', 'is_active'
        )


