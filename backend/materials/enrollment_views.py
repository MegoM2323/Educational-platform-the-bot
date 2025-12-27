"""
Subject Enrollment Endpoints - T_MAT_006

REST API endpoints for managing subject enrollments:
1. POST /api/subjects/{id}/enroll/ - Create enrollment
2. DELETE /api/subjects/{id}/unenroll/ - Cancel enrollment
3. GET /api/subjects/my-enrollments/ - List user enrollments
"""

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

from .models import SubjectEnrollment, Subject
from .serializers import (
    SubjectEnrollmentSerializer,
    SubjectEnrollmentCreateSerializer,
    SubjectEnrollmentCancelSerializer,
    MyEnrollmentsSerializer
)
from .enrollment_service import SubjectEnrollmentService, EnrollmentValidationError

User = get_user_model()


@api_view(['POST'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def enroll_subject(request, subject_id):
    """
    Enroll user in a subject - T_MAT_006

    POST /api/subjects/{subject_id}/enroll/

    Request body:
    {
        "student_id": 1,
        "teacher_id": 2,
        "custom_subject_name": "Advanced Math" (optional)
    }

    Returns:
        201: Created SubjectEnrollment
        400: Validation error (duplicate, invalid users, etc.)
        403: Permission denied
        404: Subject not found
    """
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {'error': f'Предмет с ID {subject_id} не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Validate request data
    serializer = SubjectEnrollmentCreateSerializer(
        data=request.data,
        context={'subject_id': subject_id, 'request': request}
    )

    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Create enrollment using service
        enrollment = SubjectEnrollmentService.create_enrollment(
            student_id=serializer.validated_data['student_id'],
            subject_id=subject_id,
            teacher_id=serializer.validated_data['teacher_id'],
            assigned_by=request.user if request.user.is_authenticated else None,
            custom_subject_name=serializer.validated_data.get('custom_subject_name', '')
        )

        # Serialize response
        response_serializer = SubjectEnrollmentSerializer(enrollment)
        return Response(
            {
                'success': True,
                'message': 'Студент успешно зачислен на предмет',
                'enrollment': response_serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    except EnrollmentValidationError as e:
        return Response(
            {'error': str(e.detail) if hasattr(e, 'detail') else str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при зачислении: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['DELETE'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def unenroll_subject(request, subject_id):
    """
    Unenroll user from a subject - T_MAT_006

    DELETE /api/subjects/{subject_id}/unenroll/

    Query params:
        - enrollment_id: ID of enrollment to cancel (required)

    Returns:
        200: Enrollment cancelled
        400: Validation error
        403: Permission denied
        404: Subject or enrollment not found
    """
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {'error': f'Предмет с ID {subject_id} не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Get enrollment ID from query params
    enrollment_id = request.query_params.get('enrollment_id')
    if not enrollment_id:
        return Response(
            {'error': 'Параметр enrollment_id является обязательным'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        enrollment = SubjectEnrollment.objects.get(
            id=enrollment_id,
            subject=subject
        )
    except SubjectEnrollment.DoesNotExist:
        return Response(
            {'error': f'Зачисление с ID {enrollment_id} не найдено'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Permission check - user can only unenroll themselves or admin can unenroll anyone
    if not (request.user.id == enrollment.student.id or request.user.is_staff):
        return Response(
            {'error': 'Вы не можете отменить это зачисление'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Validate request data
    serializer = SubjectEnrollmentCancelSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Cancel enrollment
        enrollment = SubjectEnrollmentService.cancel_enrollment(enrollment_id)

        return Response(
            {
                'success': True,
                'message': 'Зачисление успешно отменено',
                'enrollment': SubjectEnrollmentSerializer(enrollment).data
            },
            status=status.HTTP_200_OK
        )

    except EnrollmentValidationError as e:
        return Response(
            {'error': str(e.detail) if hasattr(e, 'detail') else str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при отмене зачисления: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def my_enrollments(request):
    """
    Get all enrollments for current user - T_MAT_006

    GET /api/subjects/my-enrollments/

    Query params:
        - active_only: Filter only active enrollments (default: true)
        - subject_id: Filter by subject ID (optional)
        - teacher_id: Filter by teacher ID (optional)
        - ordering: Sort by field (default: '-enrolled_at')

    Returns:
        200: List of SubjectEnrollment
    """
    try:
        # Get active only by default
        active_only = request.query_params.get('active_only', 'true').lower() == 'true'

        # Get enrollments for current user
        enrollments = SubjectEnrollmentService.get_student_enrollments(
            student_id=request.user.id,
            include_inactive=not active_only
        )

        # Optional filters
        subject_id = request.query_params.get('subject_id')
        if subject_id:
            try:
                subject_id = int(subject_id)
                enrollments = enrollments.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Параметр subject_id должен быть числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        teacher_id = request.query_params.get('teacher_id')
        if teacher_id:
            try:
                teacher_id = int(teacher_id)
                enrollments = enrollments.filter(teacher_id=teacher_id)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Параметр teacher_id должен быть числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Sorting
        ordering = request.query_params.get('ordering', '-enrolled_at')
        allowed_ordering = ['-enrolled_at', 'enrolled_at', 'subject__name', '-subject__name']
        if ordering in allowed_ordering:
            enrollments = enrollments.order_by(ordering)

        # Serialize
        serializer = SubjectEnrollmentSerializer(enrollments, many=True)

        return Response(
            {
                'success': True,
                'count': enrollments.count(),
                'enrollments': serializer.data
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении зачислений: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def enrollment_status(request, subject_id):
    """
    Check enrollment status for current user in a subject - T_MAT_006

    GET /api/subjects/{subject_id}/enrollment-status/

    Returns:
        200: Enrollment status
        404: Subject not found
    """
    try:
        subject = Subject.objects.get(id=subject_id)
    except Subject.DoesNotExist:
        return Response(
            {'error': f'Предмет с ID {subject_id} не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        enrollment = SubjectEnrollment.objects.select_related(
            'student', 'subject', 'teacher'
        ).get(
            student=request.user,
            subject=subject,
            is_active=True
        )

        serializer = SubjectEnrollmentSerializer(enrollment)
        return Response(
            {
                'success': True,
                'enrolled': True,
                'enrollment': serializer.data
            },
            status=status.HTTP_200_OK
        )

    except SubjectEnrollment.DoesNotExist:
        return Response(
            {
                'success': True,
                'enrolled': False,
                'enrollment': None
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'Ошибка при проверке зачисления: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def teacher_students(request, teacher_id):
    """
    Get all students enrolled with a teacher - T_MAT_006

    GET /api/teachers/{teacher_id}/students/

    Query params:
        - subject_id: Filter by subject ID (optional)
        - ordering: Sort by field (default: 'student__last_name')

    Returns:
        200: List of enrollments
        403: Forbidden (only teacher/admin can view)
        404: Teacher not found
    """
    # Permission check
    if not (request.user.id == teacher_id or request.user.is_staff):
        return Response(
            {'error': 'Вы не имеете доступа к этим данным'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Verify teacher exists
    try:
        teacher = User.objects.get(id=teacher_id, role__in=['teacher', 'tutor'])
    except User.DoesNotExist:
        return Response(
            {'error': f'Преподаватель с ID {teacher_id} не найден'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        # Get enrollments
        enrollments = SubjectEnrollmentService.get_teacher_students(
            teacher_id=teacher_id
        )

        # Optional subject filter
        subject_id = request.query_params.get('subject_id')
        if subject_id:
            try:
                subject_id = int(subject_id)
                enrollments = enrollments.filter(subject_id=subject_id)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Параметр subject_id должен быть числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Sorting
        ordering = request.query_params.get('ordering', 'student__last_name')
        allowed_ordering = ['student__last_name', '-student__last_name', 'subject__name']
        if ordering in allowed_ordering:
            enrollments = enrollments.order_by(ordering)

        # Serialize
        serializer = SubjectEnrollmentSerializer(enrollments, many=True)

        return Response(
            {
                'success': True,
                'count': enrollments.count(),
                'enrollments': serializer.data
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении студентов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
