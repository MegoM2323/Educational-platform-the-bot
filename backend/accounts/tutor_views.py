from rest_framework import status, permissions, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from materials.models import Subject
from .models import StudentProfile
from .tutor_service import StudentCreationService, SubjectAssignmentService
from .tutor_serializers import (
    TutorStudentCreateSerializer,
    TutorStudentSerializer,
    SubjectAssignSerializer,
    SubjectEnrollmentSerializer,
)


User = get_user_model()


class IsTutor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.TUTOR


class TutorStudentsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, IsTutor]

    def list(self, request):
        students = StudentProfile.objects.filter(tutor=request.user).select_related('user', 'tutor', 'parent')
        return Response(TutorStudentSerializer(students, many=True).data)

    def create(self, request):
        serializer = TutorStudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        student_user, parent_user, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
            tutor=request.user,
            student_first_name=data['first_name'],
            student_last_name=data['last_name'],
            grade=data['grade'],
            goal=data.get('goal', ''),
            parent_first_name=data['parent_first_name'],
            parent_last_name=data['parent_last_name'],
            parent_email=data.get('parent_email', ''),
            parent_phone=data.get('parent_phone', ''),
        )

        student_profile = student_user.student_profile
        response = {
            'student': TutorStudentSerializer(student_profile).data,
            'student_credentials': {
                'username': student_creds.username,
                'password': student_creds.password,
            },
            'parent_credentials': {
                'username': parent_creds.username,
                'password': parent_creds.password,
            },
        }
        return Response(response, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(id=pk, tutor=request.user)
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TutorStudentSerializer(profile).data)

    @action(detail=True, methods=['post'], url_path='subjects')
    def assign_subject(self, request, pk=None):
        # pk — это id StudentProfile
        try:
            student_profile = StudentProfile.objects.select_related('user').get(id=pk, tutor=request.user)
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден'}, status=status.HTTP_404_NOT_FOUND)

        assign_serializer = SubjectAssignSerializer(data=request.data)
        assign_serializer.is_valid(raise_exception=True)
        subject = assign_serializer.validated_data['subject']
        teacher = assign_serializer.validated_data['teacher']

        enrollment = SubjectAssignmentService.assign_subject(
            tutor=request.user,
            student=student_profile.user,
            subject=subject,
            teacher=teacher,
        )
        return Response(SubjectEnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='subjects/(?P<subject_id>[^/.]+)')
    def unassign_subject(self, request, pk=None, subject_id=None):
        try:
            student_profile = StudentProfile.objects.select_related('user').get(id=pk, tutor=request.user)
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден'}, status=status.HTTP_404_NOT_FOUND)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({'detail': 'Предмет не найден'}, status=status.HTTP_404_NOT_FOUND)

        SubjectAssignmentService.unassign_subject(
            tutor=request.user,
            student=student_profile.user,
            subject=subject,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


