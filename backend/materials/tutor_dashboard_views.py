from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from .tutor_dashboard_service import TutorDashboardService

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_dashboard(request):
    """
    Получить полные данные дашборда тьютора

    GET /api/materials/dashboard/tutor/
    """
    # Проверяем роль пользователя
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        data = service.get_dashboard_data()
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении данных дашборда: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_students(request):
    """
    Получить список студентов тьютора

    GET /api/materials/dashboard/tutor/students/
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        students = service.get_students()
        return Response({'students': students}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении списка студентов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_student_subjects(request, student_id):
    """
    Получить предметы конкретного студента

    GET /api/materials/dashboard/tutor/students/<student_id>/subjects/
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        subjects = service.get_student_subjects(student_id)
        return Response({'subjects': subjects}, status=status.HTTP_200_OK)
    except PermissionDenied as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении предметов студента: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_student_progress(request, student_id):
    """
    Получить прогресс студента

    GET /api/materials/dashboard/tutor/students/<student_id>/progress/
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        progress = service.get_student_progress(student_id)
        return Response(progress, status=status.HTTP_200_OK)
    except PermissionDenied as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении прогресса студента: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tutor_assign_subject(request):
    """
    Назначить предмет студенту

    POST /api/materials/dashboard/tutor/students/assign-subject/

    Body:
    {
        "student_id": 1,
        "subject_id": 2,
        "teacher_id": 3,
        "custom_subject_name": "Математика (углубленный курс)" (опционально)
    }
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут назначать предметы'},
            status=status.HTTP_403_FORBIDDEN
        )

    student_id = request.data.get('student_id')
    subject_id = request.data.get('subject_id')
    teacher_id = request.data.get('teacher_id')
    custom_subject_name = request.data.get('custom_subject_name')

    if not all([student_id, subject_id, teacher_id]):
        return Response(
            {'error': 'Необходимо указать student_id, subject_id и teacher_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        result = service.assign_subject(
            student_id=student_id,
            subject_id=subject_id,
            teacher_id=teacher_id,
            custom_subject_name=custom_subject_name
        )

        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {'error': f'Ошибка при назначении предмета: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def tutor_create_report(request):
    """
    Создать отчет для родителя о студенте

    POST /api/materials/dashboard/tutor/reports/create/

    Body:
    {
        "student_id": 1,
        "parent_id": 2,
        "title": "Отчет за неделю",
        "content": "Студент показал хороший прогресс...",
        "report_type": "tutor_to_parent",
        "period_start": "2025-01-01",
        "period_end": "2025-01-07",
        "progress_data": {...}
    }
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут создавать отчеты'},
            status=status.HTTP_403_FORBIDDEN
        )

    student_id = request.data.get('student_id')
    parent_id = request.data.get('parent_id')

    if not all([student_id, parent_id]):
        return Response(
            {'error': 'Необходимо указать student_id и parent_id'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        result = service.create_student_report(
            student_id=student_id,
            parent_id=parent_id,
            report_data=request.data
        )

        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {'error': f'Ошибка при создании отчета: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_reports(request):
    """
    Получить отчеты тьютора

    GET /api/materials/dashboard/tutor/reports/
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        service = TutorDashboardService(request.user, request=request)
        reports = service.get_tutor_reports()
        return Response({'reports': reports}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении отчетов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
