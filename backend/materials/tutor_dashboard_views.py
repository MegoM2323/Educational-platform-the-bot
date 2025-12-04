from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
import logging

from .tutor_dashboard_service import TutorDashboardService
from accounts.serializers import get_profile_serializer

logger = logging.getLogger(__name__)

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_dashboard(request):
    """
    Получить полные данные дашборда тьютора.

    Скрывает приватные поля профиля от самого тьютора:
    - bio (биография)
    - experience_years (опыт работы)

    GET /api/materials/dashboard/tutor/
    """
    # Проверяем роль пользователя
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = request.user
        service = TutorDashboardService(user, request=request)
        dashboard_data = service.get_dashboard_data()

        # Получаем профиль тьютора
        try:
            profile = user.tutor_profile

            # Выбираем serializer в зависимости от прав
            # Сам тьютор НЕ видит приватные поля (bio, experience_years)
            ProfileSerializer = get_profile_serializer(profile, user, user)
            serialized_profile = ProfileSerializer(profile).data

            # Добавляем профиль в dashboard_data
            dashboard_data['profile'] = serialized_profile

        except Exception as profile_error:
            logger.warning(f"Could not load tutor profile: {profile_error}")
            # Не блокируем весь dashboard если не удалось загрузить профиль
            dashboard_data['profile'] = None

        return Response(dashboard_data, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Unexpected error in tutor dashboard: {e}", exc_info=True)
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tutor_student_schedule(request, student_id):
    """
    Получить расписание занятий конкретного студента (только будущие)

    GET /api/materials/dashboard/tutor/students/<student_id>/schedule/

    Query parameters:
    - date_from: Filter by start date (optional)
    - date_to: Filter by end date (optional)
    - subject_id: Filter by subject (optional)
    - status: Filter by status (optional)

    Returns list of lessons for the specified student.
    Only works if tutor manages that student.
    """
    if request.user.role != User.Role.TUTOR:
        return Response(
            {'error': 'Только тьюторы могут получить доступ к этому ресурсу'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        # Import here to avoid circular imports
        from scheduling.services.lesson_service import LessonService
        from scheduling.serializers import LessonSerializer
        from django.utils import timezone
        from django.core.exceptions import ValidationError

        # Get lessons (validates tutor manages student)
        queryset = LessonService.get_tutor_student_lessons(
            tutor=request.user,
            student_id=student_id
        )

        # Filter by date >= today (future lessons only)
        today = timezone.now().date()
        queryset = queryset.filter(date__gte=today)

        # Apply optional query parameter filters
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        subject_id = request.query_params.get('subject_id')
        status_filter = request.query_params.get('status')

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Serialize and return
        serializer = LessonSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    except ValidationError as e:
        # ValidationError from LessonService means permission denied
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except PermissionDenied as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_403_FORBIDDEN
        )
    except Exception as e:
        logger.error(f"Error fetching student schedule: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при получении расписания студента: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
