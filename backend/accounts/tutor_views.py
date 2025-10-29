from rest_framework import status, permissions, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from django.contrib.auth import get_user_model
from django.utils import timezone

from materials.models import Subject
from .models import StudentProfile
from .tutor_service import StudentCreationService, SubjectAssignmentService
from .tutor_serializers import (
    TutorStudentCreateSerializer,
    TutorStudentSerializer,
    SubjectAssignSerializer,
    SubjectEnrollmentSerializer,
    SubjectBulkAssignSerializer,
)


User = get_user_model()


class IsTutor(permissions.BasePermission):
    def has_permission(self, request, view):
        print(f"[IsTutor] Checking permission")
        print(f"[IsTutor] Request META: {dict(request.META)}")
        print(f"[IsTutor] Authorization header: {request.META.get('HTTP_AUTHORIZATION', 'NOT SET')}")
        
        if not request.user.is_authenticated:
            print(f"[IsTutor] User not authenticated")
            print(f"[IsTutor] User object: {request.user}")
            return False
        
        user_role = getattr(request.user, 'role', None)
        print(f"[IsTutor] User: {request.user.username}, ID: {request.user.id}, Role: {user_role}, Expected: {User.Role.TUTOR}")
        
        result = user_role == User.Role.TUTOR
        if not result:
            print(f"[IsTutor] Permission denied: user role '{user_role}' != '{User.Role.TUTOR}'")
        
        return result


class TutorStudentsViewSet(viewsets.ViewSet):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsTutor]

    def list(self, request):
        print(f"[TutorStudentsViewSet.list] Request received")
        print(f"[TutorStudentsViewSet.list] User: {request.user}")
        print(f"[TutorStudentsViewSet.list] User authenticated: {request.user.is_authenticated}")
        print(f"[TutorStudentsViewSet.list] User role: {getattr(request.user, 'role', None)}")
        
        students = StudentProfile.objects.filter(tutor=request.user).select_related('user', 'tutor', 'parent')
        print(f"[TutorStudentsViewSet.list] Found {students.count()} students")
        
        serializer = TutorStudentSerializer(students, many=True)
        print(f"[TutorStudentsViewSet.list] Serialized data: {serializer.data}")
        
        return Response({
            'success': True,
            'data': serializer.data,
            'timestamp': str(timezone.now())
        })

    def create(self, request):
        print(f"[TutorStudentsViewSet.create] Request received")
        print(f"[TutorStudentsViewSet.create] User: {request.user}")
        print(f"[TutorStudentsViewSet.create] User authenticated: {request.user.is_authenticated}")
        print(f"[TutorStudentsViewSet.create] User role: {getattr(request.user, 'role', None)}")
        print(f"[TutorStudentsViewSet.create] Request data: {request.data}")
        
        serializer = TutorStudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
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
        except PermissionError as e:
            print(f"[TutorStudentsViewSet.create] PermissionError: {e}")
            return Response({'detail': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            print(f"[TutorStudentsViewSet.create] Exception: {e}")
            return Response({'detail': f'Ошибка создания ученика: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        student_profile = student_user.student_profile
        response = {
            'student': TutorStudentSerializer(student_profile).data,
            'parent': {
                'id': parent_user.id,
                'full_name': parent_user.get_full_name() or parent_user.username,
            },
            'credentials': {
                'student': {
                    'username': student_creds.username,
                    'password': student_creds.password,
                },
                'parent': {
                    'username': parent_creds.username,
                    'password': parent_creds.password,
                },
            },
        }
        return Response(response, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        try:
            profile = StudentProfile.objects.select_related('user', 'tutor', 'parent').get(id=pk, tutor=request.user)
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TutorStudentSerializer(profile).data)

    @action(detail=True, methods=['post', 'get'], url_path='subjects')
    def subjects(self, request, pk=None):
        # pk — это id StudentProfile
        try:
            student_profile = StudentProfile.objects.select_related('user').get(id=pk, tutor=request.user)
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден'}, status=status.HTTP_404_NOT_FOUND)

        if request.method.lower() == 'get':
            from materials.models import SubjectEnrollment
            enrollments = SubjectEnrollment.objects.filter(student=student_profile.user).select_related('subject', 'teacher')
            return Response(SubjectEnrollmentSerializer(enrollments, many=True).data)

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

    @action(detail=True, methods=['post'], url_path='subjects/bulk')
    def assign_subjects_bulk(self, request, pk=None):
        """Массовое назначение нескольких предметов одному ученику.
        Тело запроса: {"items": [{"subject_id": int, "teacher_id": int|null}, ...]}
        Возвращает список созданных/актуализированных зачислений.
        """
        try:
            student_profile = StudentProfile.objects.select_related('user').get(id=pk, tutor=request.user)
        except StudentProfile.DoesNotExist:
            return Response({'detail': 'Ученик не найден'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubjectBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enrollments = []
        for item in serializer.validated_data['items']:
            subject = item['subject']
            teacher = item.get('teacher')
            enrollment = SubjectAssignmentService.assign_subject(
                tutor=request.user,
                student=student_profile.user,
                subject=subject,
                teacher=teacher,
            )
            enrollments.append(enrollment)

        return Response(SubjectEnrollmentSerializer(enrollments, many=True).data, status=status.HTTP_201_CREATED)

    


