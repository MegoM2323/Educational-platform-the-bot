from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
import logging

from .student_dashboard_service import StudentDashboardService
from .models import Material, MaterialProgress, SubjectEnrollment, StudyPlan
from .serializers import MaterialListSerializer, MaterialProgressSerializer, StudyPlanSerializer, StudyPlanListSerializer
from accounts.staff_views import CSRFExemptSessionAuthentication

logger = logging.getLogger(__name__)

User = get_user_model()


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_dashboard(request):
    """
    Получить данные дашборда студента
    
    GET /api/dashboard/student/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = StudentDashboardService(request.user, request)
        dashboard_data = service.get_dashboard_data()
        return Response(dashboard_data)
    except ValueError as e:
        logger.error(f"Validation error in student dashboard: {e}")
        return Response(
            {'error': f'Ошибка валидации: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in student dashboard: {e}", exc_info=True)
        return Response(
            {'error': 'Внутренняя ошибка сервера при загрузке дашборда'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_assigned_materials(request):
    """
    Получить назначенные студенту материалы
    
    GET /api/materials/student/assigned/
    Query parameters:
    - subject_id: ID предмета для фильтрации (опционально)
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = StudentDashboardService(request.user, request)
        subject_id = request.query_params.get('subject_id')
        
        if subject_id:
            try:
                subject_id = int(subject_id)
            except ValueError:
                return Response(
                    {'error': 'subject_id должен быть числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        materials = service.get_assigned_materials(subject_id)
        return Response(materials)
    except ValueError as e:
        logger.error(f"Validation error in student materials: {e}")
        return Response(
            {'error': f'Ошибка валидации: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Unexpected error in student materials: {e}", exc_info=True)
        return Response(
            {'error': 'Внутренняя ошибка сервера при получении материалов'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_materials_by_subject(request):
    """
    Получить материалы студента, сгруппированные по предметам
    
    GET /api/materials/student/by-subject/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = StudentDashboardService(request.user, request)
        materials_by_subject = service.get_materials_by_subject()
        return Response(materials_by_subject)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении материалов по предметам: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_progress_statistics(request):
    """
    Получить статистику прогресса студента
    
    GET /api/dashboard/student/progress/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = StudentDashboardService(request.user, request)
        statistics = service.get_progress_statistics()
        return Response(statistics)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении статистики: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_recent_activity(request):
    """
    Получить недавнюю активность студента
    
    GET /api/dashboard/student/activity/
    Query parameters:
    - days: Количество дней для анализа (по умолчанию 7)
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = StudentDashboardService(request.user, request)
        days = request.query_params.get('days', 7)
        
        try:
            days = int(days)
            if days < 1 or days > 365:
                return Response(
                    {'error': 'days должен быть от 1 до 365'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'days должен быть числом'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        activity = service.get_recent_activity(days)
        return Response(activity)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении активности: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_general_chat(request):
    """
    Получить доступ к общему чату
    
    GET /api/dashboard/student/general-chat/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        service = StudentDashboardService(request.user, request)
        chat_data = service.get_general_chat_access()
        
        if chat_data is None:
            return Response(
                {'error': 'Не удалось получить доступ к общему чату'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(chat_data)
    except Exception as e:
        return Response(
            {'error': f'Ошибка при получении доступа к чату: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_subjects(request):
    """
    Получить назначенные предметы студента с преподавателями
    
    GET /api/materials/student/subjects/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        enrollments = SubjectEnrollment.objects.filter(
            student=request.user,
            is_active=True
        ).select_related('subject', 'teacher', 'assigned_by')
        
        subjects_data = []
        for enrollment in enrollments:
            subjects_data.append({
                'enrollment_id': enrollment.id,
                'subject': {
                    'id': enrollment.subject.id,
                    'name': enrollment.get_subject_name(),
                    'description': enrollment.subject.description,
                    'color': enrollment.subject.color,
                },
                'teacher': {
                    'id': enrollment.teacher.id,
                    'name': enrollment.teacher.get_full_name(),
                    'email': enrollment.teacher.email,
                },
                'assigned_by': {
                    'id': enrollment.assigned_by.id,
                    'name': enrollment.assigned_by.get_full_name(),
                } if enrollment.assigned_by else None,
                'enrolled_at': enrollment.enrolled_at,
                'is_active': enrollment.is_active,
            })
        
        return Response({'subjects': subjects_data}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting student subjects: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при получении предметов: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def update_material_progress(request, material_id):
    """
    Обновить прогресс изучения материала
    
    POST /api/materials/{material_id}/progress/
    Body:
    {
        "progress_percentage": 75,
        "time_spent": 30
    }
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Проверяем, что материал назначен студенту
        material = Material.objects.filter(
            Q(assigned_to=request.user) | Q(is_public=True),
            id=material_id,
            status=Material.Status.ACTIVE
        ).first()
        
        if not material:
            return Response(
                {'error': 'Материал не найден или не назначен студенту'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        progress_percentage = request.data.get('progress_percentage', 0)
        time_spent = request.data.get('time_spent', 0)
        
        # Валидация данных
        if not isinstance(progress_percentage, (int, float)) or progress_percentage < 0 or progress_percentage > 100:
            return Response(
                {'error': 'progress_percentage должен быть числом от 0 до 100'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(time_spent, (int, float)) or time_spent < 0:
            return Response(
                {'error': 'time_spent должен быть положительным числом'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем или обновляем прогресс
        progress, created = MaterialProgress.objects.get_or_create(
            student=request.user,
            material=material
        )
        
        progress.progress_percentage = int(progress_percentage)
        progress.time_spent += int(time_spent)
        
        # Если прогресс достиг 100%, отмечаем как завершенный
        if progress.progress_percentage >= 100:
            progress.is_completed = True
            from django.utils import timezone
            progress.completed_at = timezone.now()
        
        progress.save()
        
        serializer = MaterialProgressSerializer(progress)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'error': f'Ошибка при обновлении прогресса: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_study_plans(request):
    """
    Получить список планов занятий студента
    GET /api/materials/student/study-plans/
    Query parameters:
    - subject_id: ID предмета для фильтрации (опционально)
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        subject_id = request.query_params.get('subject_id')
        
        # Получаем отправленные и архивные планы (история доступна ученику)
        plans = StudyPlan.objects.filter(
            student=request.user,
            status__in=[StudyPlan.Status.SENT, StudyPlan.Status.ARCHIVED]
        )
        
        if subject_id:
            try:
                plans = plans.filter(subject_id=int(subject_id))
            except ValueError:
                return Response(
                    {'error': 'subject_id должен быть числом'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        plans = plans.select_related('teacher', 'subject').prefetch_related('files').order_by('-week_start_date', '-sent_at')
        serializer = StudyPlanListSerializer(plans, many=True, context={'request': request})
        
        return Response({'study_plans': serializer.data}, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in student_study_plans: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при получении планов занятий: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_study_plan_detail(request, plan_id):
    """
    Получить детали плана занятий студента
    GET /api/materials/student/study-plans/<plan_id>/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        plan = StudyPlan.objects.prefetch_related('files').get(
            id=plan_id,
            student=request.user,
            status=StudyPlan.Status.SENT
        )
        
        serializer = StudyPlanSerializer(plan, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except StudyPlan.DoesNotExist:
        return Response(
            {'error': 'План занятий не найден'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error in student_study_plan_detail: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при получении плана занятий: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@authentication_classes([TokenAuthentication, CSRFExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def student_study_plans_by_subject(request, subject_id):
    """
    Получить планы занятий студента по конкретному предмету
    GET /api/materials/student/subjects/<subject_id>/study-plans/
    """
    if request.user.role != User.Role.STUDENT:
        return Response(
            {'error': 'Доступ разрешен только студентам'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # Проверяем, что студент зачислен на этот предмет
        enrollment = SubjectEnrollment.objects.filter(
            student=request.user,
            subject_id=subject_id,
            is_active=True
        ).first()
        
        if not enrollment:
            return Response(
                {'error': 'Вы не зачислены на этот предмет'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Получаем отправленные и архивные планы по этому предмету
        plans = StudyPlan.objects.filter(
            student=request.user,
            subject_id=subject_id,
            status__in=[StudyPlan.Status.SENT, StudyPlan.Status.ARCHIVED]
        ).select_related('teacher', 'subject').prefetch_related('files').order_by('-week_start_date', '-sent_at')
        
        serializer = StudyPlanListSerializer(plans, many=True, context={'request': request})
        
        return Response({'study_plans': serializer.data}, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error in student_study_plans_by_subject: {e}", exc_info=True)
        return Response(
            {'error': f'Ошибка при получении планов занятий: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
